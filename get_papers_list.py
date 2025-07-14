import requests
import csv
from typing import List, Dict
from tqdm import tqdm

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def search_pubmed(query: str, retmax: int = 20) -> List[str]:
    print(f"Searching PubMed for: {query}")
    search_url = BASE_URL + "esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    }
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    data = response.json()
    return data["esearchresult"]["idlist"]

import xml.etree.ElementTree as ET

def fetch_details(pubmed_ids: List[str]) -> List[Dict]:
    print("Fetching detailed author data...")
    fetch_url = BASE_URL + "efetch.fcgi"
    papers = []

    for pmid in tqdm(pubmed_ids):
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml"
        }
        response = requests.get(fetch_url, params=params)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        article = root.find(".//PubmedArticle")

        if article is None:
            continue

        title = article.findtext(".//ArticleTitle", default="No Title")
        pub_date = article.findtext(".//PubDate/Year", default="Unknown Year")
        if not pub_date:
            pub_date = article.findtext(".//PubDate/MedlineDate", default="")

        authors = article.findall(".//Author")
        non_academic_authors = []
        company_affiliations = []
        email = "Not found"

        for author in authors:
            aff = author.findtext("AffiliationInfo/Affiliation", default="")
            lname = author.findtext("LastName", default="")
            fname = author.findtext("ForeName", default="")
            fullname = f"{fname} {lname}".strip()

            if aff:
                if is_company_affiliation(aff):
                    non_academic_authors.append(fullname)
                    company_affiliations.append(extract_company_name(aff))
                if "@" in aff and email == "Not found":
                    email = extract_email(aff)

        paper = {
            "PubmedID": pmid,
            "Title": title,
            "Publication Date": pub_date,
            "Non-academic Author(s)": ", ".join(non_academic_authors) or "None",
            "Company Affiliation(s)": ", ".join(set(company_affiliations)) or "None",
            "Corresponding Author Email": email
        }

        papers.append(paper)
    return papers


def save_to_csv(papers: List[Dict], filename: str):
    print(f"Saving results to {filename}...")
    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=papers[0].keys())
        writer.writeheader()
        writer.writerows(papers)
        
import re

def is_company_affiliation(aff: str) -> bool:
    aff_lower = aff.lower()
    academic_keywords = ["university", "college", "institute", "school", "hospital", "clinic", "center", "centre"]
    return not any(word in aff_lower for word in academic_keywords)

def extract_company_name(aff: str) -> str:
    # Simple heuristic: return first part before a comma
    return aff.split(",")[0]

def extract_email(aff: str) -> str:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", aff)
    return match.group(0) if match else "Not found"


import argparse

def main():
    parser = argparse.ArgumentParser(description="Search PubMed and save paper details.")
    parser.add_argument('--query', type=str, default="cancer AND immunotherapy", help='Search query for PubMed')
    parser.add_argument('--file', type=str, default="output.csv", help='Output CSV filename')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    if args.debug:
        print(f"[DEBUG] Query: {args.query}")
        print(f"[DEBUG] Output file: {args.file}")

    ids = search_pubmed(args.query)
    if args.debug:
        print(f"[DEBUG] Found PubMed IDs: {ids}")

    papers = fetch_details(ids)
    save_to_csv(papers, args.file)

    if args.debug:
        print("[DEBUG] Script completed successfully.")

if __name__ == "__main__":
    main()

