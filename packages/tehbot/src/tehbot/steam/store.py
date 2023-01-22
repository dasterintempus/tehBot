def get_app_name(soup):
    name = soup.select("#appHubAppName")[0].string
    return name

def get_app_header_url(soup):
    url = soup.select("#gameHeaderImageCtn > img")[0]["src"]
    return url