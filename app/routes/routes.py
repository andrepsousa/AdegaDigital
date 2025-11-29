from flask import render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, login_required, logout_user, current_user
from flask import (
    Blueprint, jsonify, request, render_template, url_for, flash, redirect
)
from app.models.product_models import (
    list_products, create_product, update_product,
    delete_product, product_by_id
)
from app.models.user_models import register_user
from app.models.models import Product, User
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from app.services.order_service import finalize_order
from datetime import timedelta
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename
import os
import uuid

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    product = Product.query.all()
    return render_template('index.html', product=product)


@main_bp.route('/produtos/novo', methods=["GET", "POST"],
               endpoint='create_product_view')
@login_required
def create_product_view():
    if request.method == "GET":
        return render_template('product/create.html')

    try:
        data = request.form
        image_file = request.files.get('image')
        image_path = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            # ensure uploads directory exists under static
            uploads_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            # make filename unique
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            dest = os.path.join(uploads_dir, unique_name)
            image_file.save(dest)
            # store relative path under static/ for use by templates
            image_path = os.path.join('uploads', unique_name)
        new_product_data = {
            "name": data["name"],
            "price": float(data["price"]),
                "description": data.get("description"),
            "stock": int(data.get("stock", 0) or 0),
            "image": image_path
        }

        create_product(new_product_data)
        flash("Produto criado com sucesso.", "product_success")
        return redirect(url_for('main.get_products'))
    except KeyError as e:
        flash(f"Campo faltando na requisição: {str(e)}", "product_danger")
        return render_template('product/create.html')
    except Exception as e:
        flash(f"Erro ao criar o produto: {str(e)}", "product_danger")
        return render_template('product/create.html')


@main_bp.route('/produtos/<int:id_product>/editar', methods=["GET", "POST"],
               endpoint='update_product_view')
@login_required
def update_product_view(id_product):
    product = product_by_id(id_product)
    if request.method == "GET":
        return render_template('product/edit.html', product=product)

    try:
        data = request.form
        image_file = request.files.get('image')
        image_path = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            uploads_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            dest = os.path.join(uploads_dir, unique_name)
            image_file.save(dest)
            image_path = os.path.join('uploads', unique_name)
        updated_data = {
            "name": data["name"],
            "price": float(data["price"]),
            "description": data.get("description"),
            "stock": int(data.get("stock", 0) or 0),
            # only update image if an upload happened
            **({"image": image_path} if image_path else {})
        }

        update_product(id_product, updated_data)
        flash("Produto atualizado com sucesso.", "product_success")
        return redirect(url_for('main.get_products'))
    except ValueError as e:
        flash(str(e), "product_danger")
        return render_template('product/edit.html', product=product)
    except Exception as e:
        flash(f"Erro ao atualizar o produto: {str(e)}", "product_danger")
        return render_template('product/edit.html', product=product)


@main_bp.route('/produtos/<int:id_product>/deletar', methods=["GET", "POST"],
               endpoint='delete_product_view')
@login_required
def delete_product_view(id_product):
    product = product_by_id(id_product)
    if request.method == "GET":
        return render_template('product/delete.html', product=product)

    try:
        delete_product(id_product)
        flash("Produto deletado com sucesso!", "product_success")
        return redirect(url_for('main.get_products'))
    except ValueError as e:
        flash(str(e), "product_danger")
        return redirect(url_for('main.get_products'))
    except Exception as e:
        flash(f"Erro ao deletar o produto: {str(e)}", "product_danger")
        return redirect(url_for('main.get_products'))


@main_bp.route('/produtos', methods=['GET'], endpoint='get_products')
@login_required
def get_products():
    products = list_products()
    print("Products in get_products:", products)  # Debug print
    return render_template('product/list.html', products=products)


@main_bp.route('/produtos/<int:id_product>', methods=["GET"],
               endpoint='get_products_id')
@login_required
def get_products_id(id_product):
    try:
        product = product_by_id(id_product)
        return render_template('product/detail.html', product=product)
    except ValueError as e:
        flash(str(e), "product_danger")
        return redirect(url_for('main.get_products'))
    except Exception as e:
        flash(f"Erro inesperado: {str(e)}", "product_danger")
        return redirect(url_for('main.get_products'))


@main_bp.route('/cadastro', methods=["GET", "POST"],
               endpoint='register_view')
def register_view():
    if request.method == 'GET':
        return render_template("user/register.html")

    elif request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
        except BadRequest:
            flash("Formulário inválido", "auth_danger")
            return render_template("user/register.html"), 400

        if not username or not email or not password:
            flash("Todos os campos são obrigatórios.", "auth_danger")
            return render_template("user/register.html"), 400

        try:
            user = register_user(
                username=username, email=email, password=password)
            login_user(user)
            flash("Usuário registrado com sucesso!", "auth_success")
            return redirect(url_for('main.index'))
        except ValueError as e:
            flash(f"Erro: {e}", "auth_danger")
            return render_template("user/register.html"), 400
        except Exception as e:
            flash(f"Erro inesperado: {str(e)}", "auth_danger")
            return render_template("user/register.html"), 500

    return "Método não permitido", 405


@main_bp.route('/login', methods=["GET", "POST"],
               endpoint='login')
def login():
    '''if request.method == 'GET':
        return render_template("user/login.html")'''

    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login bem-sucedido!", "auth_success")
            return redirect(url_for('main.index'))
        else:
            flash("Credenciais inválidas", "auth_danger")
    return render_template("user/login.html")


@main_bp.route('/logout', methods=['GET', 'POST'],
               endpoint='logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Logout realizado com sucesso.", "auth_success")
    return redirect(url_for('main.index'))


# ------- CARRINHO (session-based) -------

def _get_cart():
    cart = session.get('cart', {'items': {}, 'qty': 0, 'total': 0.0})
    if 'items' in cart:
        cart['items'] = {str(k): v for k, v in cart['items'].items()}
    return cart


def _recalc_cart(cart):
    qty = 0
    total = 0.0
    for item in cart['items'].values():
        qty += item['qty']
        total += item['price'] * item['qty']
    cart['qty'] = qty
    cart['total'] = total
    return cart


def _save_cart(cart):
    cart = _recalc_cart(cart)
    cart['items'] = {str(k): v for k, v in cart['items'].items()}
    session['cart'] = cart
    session.modified = True


@main_bp.route('/carrinho', methods=['GET'], endpoint='cart_view')
@login_required
def cart_view():
    cart = _get_cart()
    return render_template('cart/cart.html', cart=cart)


@main_bp.route('/carrinho/adicionar/<int:product_id>',
               methods=['POST'], endpoint='cart_add')
@login_required
def cart_add(product_id):
    qty = int(request.form.get('qty', 1))
    product = Product.query.get_or_404(product_id)

    cart = _get_cart()
    items = cart['items']
    key = str(product_id)

    if key in items:
        items[key]['qty'] += qty
    else:
        items[key] = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'qty': qty,
            'image': getattr(product, 'image', None)
        }

    _save_cart(cart)
    flash(f"‘{product.name}’ adicionado ao carrinho.", "product_success")
    return redirect(request.referrer or url_for('main.index'))


@main_bp.route('/carrinho/remover/<int:product_id>',
               methods=['POST'], endpoint='cart_remove')
@login_required
def cart_remove(product_id):
    cart = _get_cart()
    key = str(product_id)
    if key in cart['items']:
        removed = cart['items'].pop(key)
        _save_cart(cart)
        flash(f"‘{removed['name']}’ removido do carrinho.", "product_success")
    return redirect(url_for('main.cart_view'))


@main_bp.route('/carrinho/atualizar', methods=['POST'], endpoint='cart_update')
@login_required
def cart_update():
    cart = _get_cart()
    for pid, qty in request.form.items():
        if not pid.startswith('qty_'):
            continue
        product_id_str = pid.split('_', 1)[1]
        if product_id_str in cart['items']:
            cart['items'][product_id_str]['qty'] = max(1, int(qty))
    _save_cart(cart)
    flash("Carrinho atualizado.", "product_success")
    return redirect(url_for('main.cart_view'))


@main_bp.route('/carrinho/limpar', methods=['POST'], endpoint='cart_clear')
@login_required
def cart_clear():
    session['cart'] = {'items': {}, 'qty': 0, 'total': 0.0}
    flash("Carrinho limpo.", "product_success")
    return redirect(url_for('main.cart_view'))


@main_bp.route('/orders/checkout', methods=['POST'], endpoint='checkout')
@login_required
def checkout():
    # tenta usar o carrinho da sessão, senão aceita cart no body JSON
    # If quantities were submitted via form (qty_...), update the session cart first
    if request.form:
        cart = _get_cart()
        for pid, qty in request.form.items():
            if not pid.startswith('qty_'):
                continue
            product_id_str = pid.split('_', 1)[1]
            if product_id_str in cart['items']:
                cart['items'][product_id_str]['qty'] = max(1, int(qty))
        _save_cart(cart)

    cart = session.get('cart') or (request.json or {}).get('cart')
    try:
        # do not ignore stock when finalizing an order so that stock is decremented
        order, warnings, total_val = finalize_order(current_user, cart, allow_partial=True, allow_ignore_stock=False)
    except Exception as exc:
        flash(str(exc), 'product_danger')
        return redirect(url_for('main.cart_view'))

    # limpar carrinho e informar sucesso
    session.pop('cart', None)
    for w in warnings:
        flash(w, 'product_danger')
    # format total as currency R$ 1.234,56
    try:
        total_str = f"R$ {format(total_val, '.2f')}".replace('.', ',')
    except Exception:
        # fallback
        total_str = str(getattr(order, 'total_amount', ''))

    flash(f"Pedido #{order.id} finalizado (total: {total_str}).", "product_success")
    return redirect(url_for('main.index'))
