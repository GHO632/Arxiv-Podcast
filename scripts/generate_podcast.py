import datetime
import os
import xml.etree.ElementTree as ET
import requests
from textwrap import shorten

# Einfacher Arxiv-Request für q-fin (letzte 24h)
ARXIV_API = "http://export.arxiv.org/api/query"

def fetch_qfin_papers(max_results=10):
    # Suche nach q-fin Artikeln, sortiert nach Datum
    params = {
        "search_query": "cat:q-fin*",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text  # Atom-Feed als XML-Text

def parse_arxiv_feed(xml_text):
    # Sehr simple XML-Parsing-Logik
    # Für mehr Robustheit könntest du das "feedparser" Paket nutzen.
    import feedparser
    feed = feedparser.parse(xml_text)
    papers = []
    # Wir nehmen einfach alle Einträge und filtern später nach Datum
    for entry in feed.entries:
        title = entry.title
        summary = entry.summary
        link = entry.link
        authors = ", ".join(a.name for a in entry.authors)
        published = entry.published  # ISO-Format
        papers.append({
            "title": title,
            "summary": summary,
            "link": link,
            "authors": authors,
            "published": published,
        })
    return papers

def filter_papers_last_24h(papers):
    # Filtert nur die Artikel der letzten 24 Stunden
    now = datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(days=1)
    recent = []
    for p in papers:
        try:
            pub_dt = datetime.datetime.strptime(p["published"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        if pub_dt >= cutoff:
            recent.append(p)
    return recent

def build_episode_text(papers):
    if not papers:
        return "Heute keine neuen q-fin Arxiv-Artikel oder keine Treffer in den letzten 24 Stunden."

    lines = []
    lines.append("Willkommen zur heutigen Q-Fin Daily Zusammenfassung.\n")
    for i, p in enumerate(papers, start=1):
        lines.append(f"Artikel {i}: {p['title']}")
        lines.append(f"Autoren: {p['authors']}")
        # Zusammenfassung etwas kürzen, damit es nicht zu lang wird:
        short_summary = shorten(p["summary"].replace("\n", " "), width=500, placeholder="...")
        lines.append(f"Kurzüberblick: {short_summary}")
        lines.append(f"Weiterlesen: {p['link']}")
        lines.append("")  # Leerzeile
    lines.append("Das war die heutige Übersicht zu neuen Artikeln aus Quantitative Finance auf Arxiv.")
    return "\n".join(lines)

def save_episode_text(date_str, text):
    # Speichert den Text in einer Datei (z. B. später als Grundlage für TTS)
    filename = f"episodes/{date_str}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename

def update_rss(date_str, episode_title, episode_description, episode_url):
    # rss.xml laden, <item> hinzufügen, speichern
    tree = ET.parse("rss.xml")
    root = tree.getroot()
    channel = root.find("channel")

    item = ET.Element("item")
    title_el = ET.SubElement(item, "title")
    title_el.text = episode_title

    desc_el = ET.SubElement(item, "description")
    desc_el.text = episode_description

    link_el = ET.SubElement(item, "link")
    link_el.text = episode_url

    pubdate_el = ET.SubElement(item, "pubDate")
    pubdate_el.text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # enclosure ist normalerweise für Audio. Wir nutzen hier (!) erstmal Text-Datei-URL.
    enclosure_el = ET.SubElement(item, "enclosure")
    enclosure_el.set("url", episode_url)
    enclosure_el.set("type", "text/plain")

    channel.append(item)
    tree.write("rss.xml", encoding="utf-8", xml_declaration=True)

def main():
    # Datum als String
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Arxiv holen
    xml_text = fetch_qfin_papers(max_results=20)
    papers = parse_arxiv_feed(xml_text)
    recent = filter_papers_last_24h(papers)

    # 2. Episode-Text bauen
    episode_text = build_episode_text(recent)

    # 3. Episode-Datei speichern
    if not os.path.isdir("episodes"):
        os.makedirs("episodes", exist_ok=True)
    episode_file = save_episode_text(today, episode_text)

    # 4. RSS aktualisieren
    # Später, wenn du MP3 hast, sollte episode_url auf die MP3-URL zeigen.
    # Fürs erste: Text-Datei via GitHub Pages.
    username = "GHO632"  # HIER ANPASSEN
    repo_name = "Arxiv-Podcast"         # HIER ANPASSEN
    episode_url = f"https://{username}.github.io/{repo_name}/episodes/{today}.txt"
    episode_title = f"Q-Fin Daily – {today}"
    episode_description = f"Tägliche Zusammenfassung neuer q-fin Arxiv-Artikel am {today}."

    update_rss(today, episode_title, episode_description, episode_url)

if __name__ == "__main__":
    main()
