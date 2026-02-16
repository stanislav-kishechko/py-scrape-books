from typing import Generator, Any, Dict

import scrapy
from scrapy.http import Response


class BooksSpider(scrapy.Spider):
    """Spider for scraping book information from books.toscrape.com"""

    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    custom_settings = {
        "FEED_FORMAT": "jsonlines",
        "FEED_URI": "books.jl",
        "FEED_EXPORT_ENCODING": "utf-8",
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 16,
        "DOWNLOAD_DELAY": 0,
    }

    RATING_MAP = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }

    def parse(self,
              response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Parse the catalog page and follow links to individual books.

        Args:
            response: The response from the catalog page

        Yields:
            Request objects for individual book pages and next catalog page
        """
        book_links = response.css(
            "article.product_pod h3 a::attr(href)"
        ).getall()

        for link in book_links:
            yield response.follow(link, callback=self.parse_book)

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_book(self, response: Response) -> Dict[str, Any]:
        """
        Parse individual book page and extract all required information.

        Args:
            response: The response from the book detail page

        Returns:
            Dictionary containing all book information
        """
        return {
            "title": self._extract_title(response),
            "price": self._extract_price(response),
            "amount_in_stock": self._extract_stock(response),
            "rating": self._extract_rating(response),
            "category": self._extract_category(response),
            "description": self._extract_description(response),
            "upc": self._extract_upc(response),
        }

    def _extract_title(self, response: Response) -> str:
        """Extract book title from h1 tag."""
        title = response.css("h1::text").get()
        return title.strip() if title else ""

    def _extract_price(self, response: Response) -> float:
        """
        Extract and convert price to float.

        Removes currency symbols and converts to float value.
        """
        price_text = response.css("p.price_color::text").get()
        if price_text:
            price_match = response.css(
                "p.price_color::text"
            ).re_first(r"[\d.]+")
            return float(price_match) if price_match else 0.0

        return 0.0

    def _extract_stock(self, response: Response) -> int:
        """
        Extract number of items in stock.

        Parses the availability text to extract the numeric quantity.
        """
        stock_text = response.css(
            "p.instock.availability::text"
        ).re_first(r"\d+")
        return int(stock_text) if stock_text else 0

    def _extract_rating(self, response: Response) -> int:
        """
        Extract and convert star rating to number (1-5).

        The rating is stored as a class name (e.g., "One", "Two")
        which is mapped to a numeric value.
        """
        rating_class = response.css("p.star-rating::attr(class)").get()
        if rating_class:
            rating_text = rating_class.replace("star-rating ", "").strip()
            return self.RATING_MAP.get(rating_text, 0)

        return 0

    def _extract_category(self, response: Response) -> str:
        """
        Extract book category from breadcrumb navigation.

        The category is the second-to-last item in the breadcrumb.
        """
        category = response.css(
            "ul.breadcrumb li:nth-last-child(2) a::text"
        ).get()
        return category.strip() if category else ""

    def _extract_description(self, response: Response) -> str:
        """
        Extract book description from the product description section.

        The description is in a <p> tag immediately after the
        element with id "product_description".
        """
        description = response.css("#product_description + p::text").get()
        return description.strip() if description else ""

    def _extract_upc(self, response: Response) -> str:
        """
        Extract UPC (Universal Product Code) from product information table.

        UPC is in the first row of the product information table.
        """
        upc = response.css("table.table-striped tr:first-child td::text").get()
        return upc.strip() if upc else ""
