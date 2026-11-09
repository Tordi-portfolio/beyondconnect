# BeyondConnect — Django E-commerce Store

A complete e-commerce website built with Python and Django: customer sign-up/login, personal dashboards, product search with discounted prices, a shopping cart, checkout, and an admin dashboard that shows everything happening on the site.

## Features

**Storefront**
- Home page with hero search, categories, hot deals, featured products and new arrivals
- Search (`/search/?q=laptop`) across product names, descriptions and categories, with search-as-you-type suggestions
- Sort (relevance, newest, price, biggest discount, name), "on sale only" filter, category browsing, pagination
- Every product shows its **original price, discount %, discounted price, savings and description**
- Product pages with stock status, quantity picker, "Buy now" and related products
- Session-based cart, free-delivery progress bar, stock-aware quantities
- Checkout (pay on delivery / bank transfer) with stock locking so you can't oversell
- After checkout, the thank-you page counts down 5 seconds and opens WhatsApp with a pre-filled message to the store number: order reference, each item ordered (name, quantity, price, description), totals and delivery details (a button is there too if the redirect is blocked)

**Accounts**
- Sign up, log in (with **username or email**), log out, password reset (emails print to the console in development)
- Customer dashboard: order stats, recent orders, deals, profile & delivery details
- Order history, order detail, and self-service cancellation of pending orders (stock is restored)

**Admin dashboard** (`/manage/`, staff only)
- Overview: revenue, orders, customers, products, 7-day sales chart, orders by status, top sellers, low-stock alerts, newest customers
- Orders: search, filter, change status inline, full order detail
- Customers: spend and order counts per customer
- Inventory: stock, discounts and visibility, with quick links to edit
- Plus the full Django admin at `/admin/` (bulk discount actions, editable stock/discount in the product list, order inline items)

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables
python manage.py makemigrations accounts store
python manage.py migrate

# 4. Load sample categories and products (optional but recommended)
python manage.py seed_store

# 5. Create your admin account
python manage.py createsuperuser

# 6. Run the site
python manage.py runserver
```

Then open:

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/ | The store |
| http://127.0.0.1:8000/accounts/signup/ | Customer sign-up |
| http://127.0.0.1:8000/manage/ | Admin dashboard (log in as the superuser) |
| http://127.0.0.1:8000/admin/ | Full Django admin |

Run the tests with `python manage.py test`.

## Configuration

Settings live in `config/settings.py`. Useful environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev key | **Set this in production** |
| `DJANGO_DEBUG` | `1` | Set to `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | e.g. `https://example.com` |
| `STORE_CURRENCY_SYMBOL` | `₦` | Currency shown everywhere (Naira) |
| `STORE_SHIPPING_FEE` | `3500.00` | Flat delivery fee |
| `STORE_FREE_SHIPPING_THRESHOLD` | `50000.00` | Free delivery above this subtotal |
| `DJANGO_TIME_ZONE` | `UTC` | e.g. `Africa/Lagos`, `Europe/London` |
| `STORE_WHATSAPP_NUMBER` | `2347068848255` | WhatsApp number (digits only, with country code) that receives order messages |

When `DJANGO_DEBUG=0` the site enables secure cookies and an HTTPS redirect, so it must be served over HTTPS.

## Managing products

In the admin (`/admin/` → Products) set the **price** (original price) and **discount percent**; the discounted price is calculated automatically. Upload an image, or paste an image URL; products without an image get a coloured placeholder with the category icon.

## Project layout

```
config/       settings, root URLs, WSGI/ASGI
accounts/     sign-up, login, profile, customer dashboard, order history
store/        categories, products, cart, checkout, orders, search, seed command
dashboard/    staff-only admin dashboard (/manage/)
templates/    all HTML templates
static/       CSS and JavaScript
```

## Before going live

- Payments are offline (cash on delivery / bank transfer). To take card payments, integrate a gateway such as Stripe or Paystack in `store/views.py::checkout`.
- Switch SQLite to PostgreSQL, serve static files with WhiteNoise or your web server (`python manage.py collectstatic`), and serve uploaded media from storage such as S3.
- Configure a real email backend (`EMAIL_HOST`, etc.) so password-reset emails are delivered.
"# beyondconnect" 
