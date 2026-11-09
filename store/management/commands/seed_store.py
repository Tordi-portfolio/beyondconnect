from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Category, Product

CATALOG = {
    ("Electronics", "💻", "Laptops, phones, audio and smart gadgets."): [
        ("Aero Slim 14 Laptop", "Ultra-light 14-inch laptop with a bright full-HD display, 16GB RAM and a 512GB SSD. All-day battery for work and study.", "1348500.00", 20, 8, True),
        ("PulseBuds Wireless Earbuds", "Active noise-cancelling earbuds with 30 hours of battery life in the charging case and a sweat-proof design.", "120000.00", 35, 40, True),
        ("Nova 6.5\" Smartphone", "Large AMOLED screen, 128GB storage, dual cameras and fast charging. Unlocked and ready to use.", "523500.00", 15, 25, False),
        ("Smart Fitness Watch", "Tracks heart rate, sleep, steps and workouts. Water resistant with a 7-day battery and phone notifications.", "89000.00", 30, 50, False),
    ],
    ("Fashion", "👗", "Clothing, shoes and accessories for every day."): [
        ("Classic Denim Jacket", "Timeless medium-wash denim jacket with a soft cotton lining. A wardrobe staple for every season.", "96000.00", 25, 18, True),
        ("Everyday Leather Sneakers", "Minimal white leather sneakers with cushioned insoles and a durable rubber sole.", "133500.00", 15, 30, False),
        ("Weekender Canvas Backpack", "Roomy 25L backpack with a padded laptop sleeve, water-resistant canvas and leather straps.", "81000.00", 0, 22, False),
        ("Polarised Aviator Sunglasses", "Lightweight metal frame with UV400 polarised lenses. Includes a hard case and cleaning cloth.", "58500.00", 40, 60, False),
    ],
    ("Home & Kitchen", "🏠", "Make your home comfortable and your cooking easier."): [
        ("Pro Air Fryer 5L", "Cook crispy meals with up to 80% less oil. Digital touch controls, 8 presets and a dishwasher-safe basket.", "178500.00", 30, 14, True),
        ("Ceramic Non-Stick Cookware Set (8pc)", "Even-heating, PFOA-free ceramic cookware with heat-resistant handles and glass lids.", "208500.00", 10, 12, False),
        ("Soft Linen Duvet Cover Set", "Breathable washed-linen duvet cover with two pillowcases. Gets softer with every wash.", "108000.00", 0, 33, False),
        ("Aroma Diffuser & Night Light", "Ultrasonic essential-oil diffuser with 7 ambient colours and an automatic shut-off.", "42000.00", 20, 45, False),
    ],
    ("Beauty & Care", "💄", "Skincare, haircare and grooming essentials."): [
        ("Vitamin C Brightening Serum", "Daily serum with 15% vitamin C and hyaluronic acid for a more even, glowing complexion.", "48000.00", 20, 70, True),
        ("Ionic Hair Dryer 2200W", "Fast-drying ionic dryer with three heat settings, a cool shot button and a concentrator nozzle.", "87000.00", 15, 26, False),
        ("Beard & Grooming Kit", "Trimmer, scissors, comb, brush and beard oil in a gift-ready travel case.", "67500.00", 0, 38, False),
        ("Shea Butter Body Lotion (400ml)", "Rich, fast-absorbing daily moisturiser with shea butter and vitamin E. Fragrance-light.", "22000.00", 10, 90, False),
    ],
    ("Sports & Fitness", "🏋️", "Gear for training, running and the outdoors."): [
        ("Non-Slip Yoga Mat 6mm", "Extra-thick, eco-friendly mat with alignment lines and a carry strap.", "39000.00", 25, 55, False),
        ("Adjustable Dumbbell Pair (2-24kg)", "Space-saving adjustable dumbbells that replace 15 sets of weights. Quick-dial weight selection.", "283500.00", 18, 9, True),
        ("Insulated Steel Water Bottle 1L", "Keeps drinks cold for 24 hours or hot for 12. Leak-proof lid and BPA-free.", "31500.00", 0, 120, False),
        ("Trail Running Shoes", "Grippy outsole, breathable mesh and responsive cushioning for road-to-trail runs.", "141000.00", 20, 17, False),
    ],
    ("Books & Stationery", "📚", "Notebooks, planners and desk accessories."): [
        ("Hardcover Dotted Notebook (A5)", "Lay-flat binding, 160 gsm ivory paper that handles fountain pens and markers without bleed-through.", "19500.00", 0, 150, False),
        ("Weekly Planner & Goal Journal", "Undated planner with weekly spreads, habit tracker and monthly reflection pages.", "27000.00", 15, 65, False),
        ("Ergonomic Desk Lamp", "Dimmable LED lamp with five colour temperatures, USB charging port and a flexible arm.", "54000.00", 30, 28, True),
        ("Gel Pen Set (24 colours)", "Smooth-writing, quick-dry gel pens in a rainbow of colours. Perfect for notes and journaling.", "14000.00", 20, 200, False),
    ],
}


class Command(BaseCommand):
    help = "Create sample categories and products (safe to run more than once)."

    def handle(self, *args, **options):
        created_products = 0
        for (cat_name, icon, description), products in CATALOG.items():
            category, _ = Category.objects.get_or_create(
                name=cat_name, defaults={"icon": icon, "description": description}
            )
            for name, desc, price, discount, stock, featured in products:
                _, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        "category": category,
                        "description": desc,
                        "price": Decimal(price),
                        "discount_percent": discount,
                        "stock": stock,
                        "is_featured": featured,
                    },
                )
                created_products += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_products} new product(s) added; "
            f"{Category.objects.count()} categories and {Product.objects.count()} products in total."
        ))
