from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException  # Import TimeoutException
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
import time

# Initialize the Chrome driver
driver = webdriver.Chrome()

# List to store the results
papers = []

# Function to scrape data from the IEEE page
def scrape_current_page():
    try:
        # Wait for paper elements to load
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'result-item-align')))
    except TimeoutException:
        print("Timeout waiting for papers to load.")
        return  # Skip if elements are not loaded

    # Parse with BeautifulSoup
    page_soup = BeautifulSoup(driver.page_source, "html.parser")
    paper_tags = page_soup.find_all('div', class_='result-item-align')

    # Use tqdm to show progress for each article on the page
    for paper_tag in tqdm(paper_tags, desc="Processing articles on current page"):
        # Extract paper title and URL
        title_tag = paper_tag.find('a', href=True)
        paper_title = title_tag.get_text(strip=True) if title_tag else "Title Not Found"
        paper_url = f"https://ieeexplore.ieee.org{title_tag['href']}" if title_tag and title_tag['href'] else "URL Not Found"

        # Find corresponding authors
        authors_tag = paper_tag.find('p', class_='author')
        authors = []

        if authors_tag:  # Proceed only if there are authors listed
            for author_tag in authors_tag.find_all('a', href=True):
                author_name = author_tag.get_text(strip=True)
                author_profile_url = f"https://ieeexplore.ieee.org{author_tag['href']}"

                # Retry loading author profile page to get affiliation
                attempts = 3
                for attempt in range(attempts):
                    try:
                        driver.get(author_profile_url)
                        time.sleep(3)  # Wait for the author's page to load
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CLASS_NAME, 'current-affiliation'))
                        )  # Wait for the affiliation section
                        break  # Exit the retry loop if successful
                    except TimeoutException:
                        if attempt < attempts - 1:
                            print(f"Retrying loading author profile for {author_name} (Attempt {attempt + 2})")
                            time.sleep(5)  # Extra wait before retrying
                        else:
                            print(f"Failed to load author profile for {author_name} after {attempts} attempts.")
                            affiliation = "N/A"
                            continue

                # Parse for affiliation
                author_soup = BeautifulSoup(driver.page_source, "html.parser")
                affiliation_section = author_soup.find('div', class_='current-affiliation')

                if affiliation_section:
                    # Extract all <div> elements inside the affiliation section and join their text
                    all_affiliation_lines = [
                        div.get_text(strip=True) for div in affiliation_section.find_all('div') if div.get_text(strip=True)
                    ]
                    affiliation = ", ".join(all_affiliation_lines)  # Combine with a comma and space
                else:
                    affiliation = "N/A"

                authors.append({"name": author_name, "profile_url": author_profile_url, "affiliation": affiliation})

                # Navigate back to the main page
                driver.back()
                time.sleep(3)  # Wait before next author fetch

        papers.append({"title": paper_title, "url": paper_url, "authors": authors})

# Start scraping each page
for page_num in range(1, 72):  # 71 pages in total
    print(f"\nScraping page {page_num}")
    url = f"https://ieeexplore.ieee.org/xpl/conhome/10609961/proceeding?isnumber=10609862&sortType=vol-only-seq&pageNumber={page_num}"
    driver.get(url)
    scrape_current_page()
    time.sleep(3)  # Small delay to avoid overwhelming the server

# Close the driver
driver.quit()

# Convert the data to a DataFrame and save as CSV
data = []
for paper in papers:
    for author in paper["authors"]:
        data.append({
            "Paper Title": paper["title"],
            "Paper URL": paper["url"],
            "Author Name": author["name"],
            "Author Profile URL": author.get("profile_url", "N/A"),
            "Author Affiliation": author.get("affiliation", "N/A")
        })

df = pd.DataFrame(data)
df.to_csv("IEEE_Xplore_Papers.csv", index=False)

print("Data saved to IEEE_Xplore_Papers.csv")
