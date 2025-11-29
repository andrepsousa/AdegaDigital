from app.utils import db
from app.models.models import Product


def list_products():
    products = Product.query.all()
    result = [
        {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "stock": getattr(product, 'stock', 0),
            "image": getattr(product, 'image', None),
            "description": product.description
        }
        for product in products
    ]
    print("Products:", result)  # Debug print
    return result


def product_by_id(id_product):
    product = Product.query.get(id_product)
    if product:
        return {
            "id": product.id,
            "nome": product.name,
            "preco": product.price,
            "descricao": product.description,
            "image": getattr(product, 'image', None),
            "stock": getattr(product, 'stock', 0)
        }
    raise ValueError("Produto não encontrado.")


def create_product(data):
    try:

        if not data.get("name") or not data.get("price"):
            raise ValueError("O nome e o preço do produto são obrigatórios.")
        if data.get("price") > 0:

            stock = int(data.get("stock", 0) or 0)

            new_product = Product(
                name=data.get("name"),
                price=data.get("price"),
                description=data.get("description"),
                stock=stock,
                image=data.get('image')
            )

            db.session.add(new_product)
            db.session.commit()

            return new_product

        else:
            raise ValueError("O valor do produto deve ser positivo.")
    except Exception as e:
        db.session.rollback()
        print(f'Erro ao adicionar produto {e}')
        raise e


def update_product(id_product, new_data):
    product = Product.query.get(id_product)
    if not product:
        raise ValueError("Product not found!")

    print(f"Found product: {product}")

    product.name = new_data.get("name", product.name)
    product.price = new_data.get("price", product.price)
    product.description = new_data.get("description", product.description)
    # update stock if provided
    if 'stock' in new_data:
        try:
            product.stock = int(new_data.get('stock', product.stock))
        except Exception:
            pass

    # update image if provided
    if 'image' in new_data:
        try:
            product.image = new_data.get('image')
        except Exception:
            pass

    db.session.commit()

    return product


def delete_product(id_product):
    product = Product.query.get(id_product)
    if not product:
        raise ValueError("Product not found!")
    try:
        db.session.delete(product)
        db.session.commit()
        return product
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting product: {e}")
        raise e
