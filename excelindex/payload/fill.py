from pathlib import Path
import pandas as pd
from models import Order, OrderProduct, Product, Pvz, User


def fill_u(file):
    df = pd.read_excel(file)
    try:
        for idx, row in df.iterrows():
            fio = row["ФИО"].split(" ")
            User.create(
                first_name=fio[0],
                last_name=fio[1],
                middle_name=fio[2],
                login=row["Логин"],
                password=row["Пароль"],
                role=row["Роль сотрудника"],
            )
    except Exception as e:
        print(f"Произошла ошибка в создании Юзера: {e}")


def fill_pvz(file):
    df = pd.read_excel(file)
    try:
        for idx, row in df.iterrows():
            address_str = str(row.iloc[0])
            address_str = address_str.replace("\xa0", "")
            fields = address_str.split(", ")
            Pvz.create(
                idx=fields[0],
                city=fields[1],
                street=fields[2],
                building=fields[3],
            )
    except Exception as e:
        print(f"Произошла ошибка в создании ПВЗ: {e}")


def fill_t(file):
    df = pd.read_excel(file)
    try:
        for idx, row in df.iterrows():
            Product.create(
                articul=row["Артикул"],
                name=row["Наименование товара"],
                ed_izm=row["Единица измерения"],
                price=row["Цена"],
                supplier=row["Поставщик"],
                creator=row["Производитель"],
                category=row["Категория товара"],
                discount=row["Действующая скидка"],
                quantity=row["Кол-во на складе"],
                description=row["Описание товара"],
                photo=row["Фото"],
            )
    except Exception as e:
        print(f"Произошла ошибка в создании Товара: {e}")


def fill_o(file):
    df = pd.read_excel(file)
    try:
        for idx, row in df.iterrows():
            fio = row["ФИО авторизированного клиента"].split(" ")
            client = User.get(
                User.first_name == fio[0],
                User.last_name == fio[1],
                User.middle_name == fio[2],
            )
            Order.create(
                number=row["Номер заказа"],
                order_date=row["Дата заказа"],
                delivery_date=row["Дата доставки"],
                pvz_id=row["Адрес пункта выдачи"],
                client_id=client.id,
                code=row["Код для получения"],
                status=row["Статус заказа"],
            )
    except Exception as e:
        print(f"Произошла ошибка в создании Заказа: {e}")


def fill_ot(file):
    df = pd.read_excel(file)
    try:
        for idx, row in df.iterrows():
            data = row["Артикул заказа"].split(", ")
            order = Order.get(Order.number == row["Номер заказа"])
            products = Product.select().where(Product.articul.in_((data[0], data[2])))
            OrderProduct.create(
                order_id=order.id,
                product_id=products[0].id,
                quantity=data[1],
            )
            OrderProduct.create(
                order_id=order.id,
                product_id=products[1].id,
                quantity=data[3],
            )
    except Exception as e:
        print(f"Произошла ошибка в создании ЗТ: {e}")


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    fill_u(BASE_DIR / "import" / "user_import.xlsx")
    fill_pvz(BASE_DIR / "import" / "Пункты выдачи_import.xlsx")
    fill_t(BASE_DIR / "import" / "Tovar.xlsx")
    fill_o(BASE_DIR / "import" / "Заказ_import.xlsx")
    fill_ot(BASE_DIR / "import" / "Заказ_import.xlsx")
