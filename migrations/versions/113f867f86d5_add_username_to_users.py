from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "113f867f86d5"
down_revision = None  # ou mantenha o valor que já estava
branch_labels = None
depends_on = None


def upgrade():
    # 1) adiciona a coluna como NULLable (SQLite não deixa NOT NULL direto)
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("username", sa.String(length=50), nullable=True))

    # 2) preenche valores provisórios (ajuste a regra se preferir)
    op.execute("UPDATE users SET username = email WHERE username IS NULL")

    # 3) torna NOT NULL e cria UNIQUE com NOME
    with op.batch_alter_table("users") as batch:
        batch.alter_column("username", existing_type=sa.String(50), nullable=False)
        batch.create_unique_constraint("uq_users_username", ["username"])

    # (opcional) garantir UNIQUE em email com NOME; usa índice único para evitar
    # diferenças entre 'index' e 'constraint' no SQLite.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON users (email)"
    )


def downgrade():
    # rollback: remove UNIQUE e coluna
    with op.batch_alter_table("users") as batch:
        # Em SQLite o índice único pode ser removido por SQL bruto
        pass
    op.execute("DROP INDEX IF EXISTS uq_users_email")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_username", type_="unique")
        batch.drop_column("username")
