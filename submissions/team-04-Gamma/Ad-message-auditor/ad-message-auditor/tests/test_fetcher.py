from fetcher import check_public_url, fetch_html


def test_blocks_unsafe_urls():
    for url in ["ftp://example.com/x", "http://localhost/a", "http://127.0.0.1/", "http://10.0.0.5/",
                "http://192.168.1.1/", "http://169.254.169.254/latest/meta-data", "http://[::1]/",
                "http://example.com:8080/", "http://user:pw@93.184.216.34/", "http://printer.local/"]:
        ok, reason = check_public_url(url)
        assert not ok, url
    assert fetch_html("http://127.0.0.1/").error.startswith("Blocked")


def test_allows_public_ip_literal():
    assert check_public_url("https://93.184.216.34/")[0] is True
