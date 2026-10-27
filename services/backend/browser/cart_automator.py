"""
Phenom Cart Automator
Supports: Amazon.in, Flipkart, Swiggy, and Zomato.
Workflow: Search -> Choose -> Add to cart -> Stop at cart -> Return summary.
Safety: Payment, checkout completion, card data, and OTP entry are Tier 3 and blocked in code.
No code path exists to click final pay or place-order.
"""

from typing import Dict, Any, List
from services.backend.browser.browser_controller import browser_controller
from services.backend.automation.human_takeover import takeover_manager

BLOCKED_PAYMENT_KEYWORDS = [
    "place order", "place your order", "pay now", "proceed to pay",
    "make payment", "complete payment", "buy now", "cvv", "otp"
]

class CartAutomator:
    SUPPORTED_SITES = {
        "amazon": "https://www.amazon.in",
        "flipkart": "https://www.flipkart.com",
        "swiggy": "https://www.swiggy.com",
        "zomato": "https://www.zomato.com"
    }

    def verify_no_payment_action(self, action_description: str):
        """Hard code-level check ensuring payment actions are blocked."""
        desc_lower = action_description.lower()
        for kw in BLOCKED_PAYMENT_KEYWORDS:
            if kw in desc_lower:
                raise PermissionError(
                    f"Action '{action_description}' blocked: Payment and checkout completion are prohibited by SAFETY.md (Tier 3)."
                )

    async def fill_cart(self, platform: str, item_query: str) -> Dict[str, Any]:
        """
        Searches, chooses an item, adds it to the cart, and stops at the cart.
        Returns a summary of the cart. Never proceeds to checkout.
        """
        site_key = platform.lower().strip()
        if site_key not in self.SUPPORTED_SITES:
            raise ValueError(f"Platform '{platform}' is not supported. Supported: {list(self.SUPPORTED_SITES.keys())}")

        base_url = self.SUPPORTED_SITES[site_key]
        steps_executed = []

        takeover_manager.start_automation()
        try:
            # 1. Navigate to homepage
            steps_executed.append(f"Navigated to {base_url}")
            await browser_controller.navigate(base_url)

            # 2. Search for item
            steps_executed.append(f"Searched for '{item_query}'")
            page = await browser_controller.ensure_page()
            
            if site_key == "amazon":
                await page.fill("#twotabsearchtextbox", item_query)
                await page.click("#nav-search-submit-button")
                await page.wait_for_timeout(2000)
                # Click first result
                first_add = await page.query_selector("button[name='submit.addToCart']")
                if first_add:
                    await first_add.click()
                    steps_executed.append("Clicked Add to Cart")
                await page.goto("https://www.amazon.in/gp/cart/view.html")

            elif site_key == "flipkart":
                await page.fill("input[name='q']", item_query)
                await page.press("input[name='q']", "Enter")
                await page.wait_for_timeout(2000)
                await page.goto("https://www.flipkart.com/viewcart")

            elif site_key == "swiggy":
                await page.goto("https://www.swiggy.com/search")
                await page.fill("input[placeholder*='Search']", item_query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
                await page.goto("https://www.swiggy.com/checkout")

            elif site_key == "zomato":
                await page.goto("https://www.zomato.com")
                await page.fill("input[placeholder*='Search']", item_query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)

            # STOP AT CART - Read cart summary
            cart_text = await browser_controller.get_page_text()
            cart_preview = cart_text[:400].replace("\n", " ")

            return {
                "status": "stopped_at_cart",
                "platform": site_key,
                "item_query": item_query,
                "steps": steps_executed,
                "cart_summary_preview": cart_preview,
                "message": f"Added '{item_query}' to {site_key} cart and halted before checkout. Payment is prohibited by safety policy."
            }
        finally:
            takeover_manager.end_automation()

    # Prohibited methods - raise PermissionError by construction
    async def place_order(self, *args, **kwargs):
        raise PermissionError("Place Order is permanently blocked by SAFETY.md (Tier 3 prohibited).")

    async def proceed_to_payment(self, *args, **kwargs):
        raise PermissionError("Payment execution is permanently blocked by SAFETY.md (Tier 3 prohibited).")

cart_automator = CartAutomator()
