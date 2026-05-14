from peewee import (
    CharField,
    DateField,
    DecimalField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
    PostgresqlDatabase,
)

db = SqliteDatabase("db.db")
# db = PostgresqlDatabase(
#     "db",
#     user="postgres",
#     password="postgres",
#     host="127.0.0.1",
#     port=5432
# )


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    first_name = CharField()
    last_name = CharField()
    middle_name = CharField()
    login = CharField()
    password = CharField()
    role = CharField()


class Pvz(BaseModel):
    idx = CharField()
    city = CharField()
    street = CharField()
    building = CharField()


class Product(BaseModel):
    articul = CharField()
    name = CharField()
    ed_izm = CharField()
    price = DecimalField(25, 2)
    supplier = CharField()
    creator = CharField()
    category = CharField()
    discount = IntegerField(default=0)
    quantity = IntegerField(default=0)
    description = TextField()
    photo = CharField()


class Order(BaseModel):
    number = IntegerField()
    order_date = DateField()
    delivery_date = DateField()
    code = CharField()
    status = CharField()

    pvz = ForeignKeyField(Pvz)
    client = ForeignKeyField(User)


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="items")
    product = ForeignKeyField(Product, backref="order_items")
    quantity = IntegerField(default=1)


if __name__ == "__main__":
    MODELS = [User, Pvz, Product, Order, OrderProduct]
    db.connect()
    db.create_tables(MODELS, safe=True)
    print("created")
