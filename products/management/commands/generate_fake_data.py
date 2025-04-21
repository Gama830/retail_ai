from django.core.management.base import BaseCommand
from faker import Faker
from random import randint, choice, uniform
from datetime import timedelta, datetime
from django.utils.timezone import make_aware
from products.models import Product, ProductCategory
from customers.models import Customer
from billing.models import Sale, SaleItem

fake = Faker('en_IN')

class Command(BaseCommand):
    help = 'Generate fake data: customers, products, and sales'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Generating fake data...")

        # --- Create Categories ---
        categories = []
        for _ in range(10):
            name = fake.unique.word().capitalize()
            category, _ = ProductCategory.objects.get_or_create(name=name)
            categories.append(category)
        self.stdout.write("✅ Product categories created")

        # --- Create Products ---
        products = []
        for _ in range(50):
            category = choice(categories)
            product = Product.objects.create(
                name=fake.unique.word().capitalize(),
                category=category,
                brand=fake.company(),
                size=choice(['S', 'M', 'L', 'XL']),
                color=fake.color_name(),
                cost_price=round(uniform(200, 1000), 2),
                selling_price=round(uniform(300, 1500), 2),
                stock_quantity=randint(50, 200)
            )
            products.append(product)
        self.stdout.write("✅ Products created")

        # --- Create Customers ---
        customers = []
        for _ in range(100):
            customer = Customer.objects.create(
                name=fake.name(),
                phone=fake.unique.phone_number()[:15],
                email=fake.email(),
                address=fake.address(),
                city=fake.city(),
                state=fake.state(),
                pincode=fake.postcode(),
                tag=choice(['vip', 'regular', 'new']),
            )
            customers.append(customer)
        self.stdout.write("✅ Customers created")

        # --- Generate Sales ---
        today = datetime.now()
        start_date = today - timedelta(days=180)

        for day in range(180):
            sale_date = make_aware(start_date + timedelta(days=day))
            for _ in range(randint(5, 15)):  # sales per day
                customer = choice(customers)
                sale = Sale.objects.create(
                    customer=customer,
                    date=sale_date,
                    total_amount=0  # updated after items
                )

                total = 0
                for _ in range(randint(1, 5)):  # items per sale
                    product = choice(products)
                    quantity = randint(1, 4)
                    price = float(product.selling_price)
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        price=price
                    )
                    total += quantity * price

                sale.total_amount = total
                sale.save()

                # Update customer stats
                customer.total_spent += total
                customer.visit_count += 1
                customer.last_purchase_date = sale_date
                customer.save()

        self.stdout.write("✅ Sales data generated")
        self.stdout.write(self.style.SUCCESS("🎉 Fake data generation complete!"))
