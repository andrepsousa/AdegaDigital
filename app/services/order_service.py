from decimal import Decimal
from app.utils import db
from app.models.models import Order, OrderItem, OrderStatus, Product


def _normalize_cart(cart):
    if not cart:
        return []
    if isinstance(cart, list):
        return cart
    # assume dict of {product_id: {id, name, price, qty}} or {product_id: qty}
    items = []
    # support session cart structure used in routes: {'items': {pid: {id, name, price, qty}}}
    if isinstance(cart, dict) and 'items' in cart:
        for pid, info in cart['items'].items():
            items.append({'product_id': int(pid), 'quantity': int(info.get('qty', info.get('quantity', 0)))})
        return items

    # fallback: dict {pid: qty}
    for k, v in cart.items():
        items.append({'product_id': int(k), 'quantity': int(v)})
    return items


def finalize_order(user, cart, allow_partial=False, allow_ignore_stock=False):
    """Transforma o carrinho em um Order persistido.

    Lança ValueError em caso de erro (carrinho vazio, produto inexistente, estoque insuficiente).
    Retorna a instância Order criada.
    """
    items = _normalize_cart(cart)
    if not items:
        raise ValueError('Carrinho vazio')

    # Use a nested transaction (SAVEPOINT) to avoid "A transaction is already begun on this Session"
    # which can occur when the Flask app/request context already started a transaction.
    warnings = []
    try:
        with db.session.begin_nested():
            order = Order(user_id=user.id, status=OrderStatus.PENDING.value, total_amount=Decimal('0.00'))
            db.session.add(order)
            total = Decimal('0.00')

            for entry in items:
                pid = int(entry['product_id'])
                qty = int(entry['quantity'])
                product = db.session.get(Product, pid)
                if product is None:
                    raise ValueError(f'Produto {pid} não encontrado')

                available = getattr(product, 'stock', None)
                used_qty = qty
                # If ignoring stock, always use requested qty and do not decrement stock below
                if allow_ignore_stock:
                    used_qty = qty
                    decrement_stock = False
                else:
                    decrement_stock = True
                    if available is not None and available < qty:
                        if allow_partial:
                            if available > 0:
                                used_qty = available
                                warnings.append(f"Quantidade do produto '{product.name}' reduzida de {qty} para {used_qty} por falta de estoque.")
                            else:
                                # silently skip items with zero stock (no warning requested)
                                continue
                        else:
                            raise ValueError(f'Estoque insuficiente para produto {product.name}')

                unit_price = Decimal(str(getattr(product, 'price', 0)))
                total += unit_price * used_qty

                # debit stock by the used quantity (unless we're purposely ignoring stock)
                if decrement_stock and getattr(product, 'stock', None) is not None and used_qty > 0:
                    product.stock = product.stock - used_qty
                    db.session.add(product)

                oi = OrderItem(order=order, product_id=pid, quantity=used_qty, unit_price=unit_price,
                               product_image=getattr(product, 'image', None))
                db.session.add(oi)

            order.total_amount = total
            # marca como PAID por enquanto (integração de pagamento pode alterar)
            order.status = OrderStatus.PAID.value
            db.session.add(order)

        # commit the outer transaction
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return order, warnings, total
