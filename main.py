import traceback
from datetime import datetime
from time import sleep

import requests
from bs4 import BeautifulSoup
from lxml import etree

import config


"""
Main method doing all the crawling
"""
def main():
    # Create a session
    with requests.Session() as s:
        # Get initial game view (first 50 games) which also includes total games count
        r = s.get("https://www.speedrun.com/ajax_games.php?game=&platform=&unofficial=off&orderby=mostplayers&title=&series=&start=0")
        # Parse HTML to be manipulatable
        soup = BeautifulSoup(r.content, "html.parser")
        dom = etree.HTML(str(soup))
        # Get games count
        count_of_games = dom.xpath('/html/body/div[1]')[0].text
        # Can only query 50 games at once. Therefor calculate how many pages of games there are
        pagination_count = int(int(count_of_games.strip().replace(" results", "").replace(",", "")) / 50)

        game_stats_hrefs = []
        # Get all games (their href) in a list (stop when games have players < config.min_player_numer)
        for x in range(pagination_count+1):
            calculated_pagination = str(x * 50)
            # Get current 50 games
            r = s.get("https://www.speedrun.com/ajax_games.php?game=&platform=&unofficial=off&orderby=mostplayers&title=&series=&start="+calculated_pagination)
            soup = BeautifulSoup(r.content, "html.parser")
            dom = etree.HTML(str(soup))
            games = dom.xpath("/html/body/div[contains(@class, 'gamelistcell')]")
            BREAK_FLAG = False
            # Iterate over the 50 games in current view and save to list if enough players play it
            for game in list(games):
                player_count = int(game.xpath(".//p")[0].text.strip().replace(" total players", "").replace(",", ""))
                # Break out and stop iteration if player count to low
                if player_count < config.min_player_numer:
                    BREAK_FLAG = True
                    print("Games to crawl:", len(game_stats_hrefs))
                    break
                href = game.xpath(".//a")[0].attrib['href']
                # Save gama with /gamestats to directly access game stats
                game_stats_hrefs.append("https://www.speedrun.com" + href + "/gamestats")
            if BREAK_FLAG:
                break

        # Clear file
        with open("data.csv", "w") as f: 
            f.write("name;players;posts\n")
        # Write CSV headers
        with open("data.csv", "a") as f:
            # Extract stats of each game and write to file
            for index, game in enumerate(game_stats_hrefs):
                try:
                    # Get current game
                    r = s.get(game, timeout=5)

                    soup = BeautifulSoup(r.content, "html.parser")
                    dom = etree.HTML(str(soup))
                    # Get game name + year
                    ele = dom.xpath("//div[@id='profile-menu']//div[@class='widget-title']")[0]
                    name = ele.xpath("string()")

                    total_amount_players = ""
                    total_amount_posts = ""
                    all_stats = dom.xpath("//div[@class='row row-list']")
                    # Iterate over all stats on page and only save the stats which are defined in if clauses
                    for stat in all_stats:
                        if "Number of players total" in stat.xpath(".//div[1]")[0].text:
                            total_amount_players = stat.xpath(".//div[1]")[0].text.strip(), stat.xpath(".//div[2]")[0].text.strip()
                        elif "Number of posts" in stat.xpath(".//div[1]")[0].text:
                            total_amount_posts = stat.xpath(".//div[1]")[0].text.strip(), stat.xpath(".//div[2]")[0].text.strip()
                    print(str(index + 1) + ":", name, total_amount_players, total_amount_posts)
                    # Write all to file
                    f.write(name + ";" + total_amount_players[1].replace(",", "") + ";" + total_amount_posts[1].replace(",", "") + "\n")
                # In case of timeout (stats not reachable atm) write and error line to the CSV for manual checking
                except requests.exceptions.ReadTimeout:
                    print(game, "timed out!")
                    f.write(game + ";N/A;N/A\n")
                # Sleep fixed amoutn of time to not overload the server
                sleep(config.wait_between_games_sec)


"""
Method to write a stacktrace to a file for better debugging
"""
def write_error_to_file():
    timestamp = str(datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))
    with open("error_" + timestamp + ".log", "w") as f:
        f.write(traceback.format_exc())
    print("Error dumped to file error_" + timestamp + ".log\n")


"""
Entry Point
"""
if __name__ == "__main__":
    try:
        # Start main method
        main()
    # In case of any exception
    except Exception:
        if config.dev_mode:
            traceback.print_exc()
        else:
            print("\nOh no! There was an error whilst running the application.")
            write_error_to_file()
    # In case of the user closing the application early
    except KeyboardInterrupt:
        print("\nApplication closed prematurely!\n")
    finally:
        print("Goodbye!")
