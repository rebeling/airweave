"""Make cron_schedule optional

Revision ID: bafb02fba223
Revises: 1ebb07e18a07
Create Date: 2025-01-02 23:19:43.528878

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bafb02fba223'
down_revision = '1ebb07e18a07'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sync', 'cron_schedule',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sync', 'cron_schedule',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    # ### end Alembic commands ###
