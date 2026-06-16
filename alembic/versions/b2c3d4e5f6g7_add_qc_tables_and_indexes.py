"""add_qc_tables_and_indexes

Revision ID: b2c3d4e5f6g7
Revises: a3b15996ec7b
Create Date: 2026-06-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a3b15996ec7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('qc_reference_images',
    sa.Column('ref_image_id', sa.String(length=36), nullable=False),
    sa.Column('project_id', sa.String(length=36), nullable=False),
    sa.Column('milestone_type', sa.String(length=64), nullable=True),
    sa.Column('image_path', sa.String(length=512), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('uploaded_by_actor_id', sa.String(length=36), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('ref_image_id')
    )
    op.create_index('ix_qc_reference_images_project_id', 'qc_reference_images', ['project_id'], unique=False)

    op.create_table('qc_process_cards',
    sa.Column('process_card_id', sa.String(length=36), nullable=False),
    sa.Column('project_id', sa.String(length=36), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=False),
    sa.Column('material_spec', sa.Text(), nullable=True),
    sa.Column('color_spec', sa.String(length=256), nullable=True),
    sa.Column('size_spec', sa.Text(), nullable=True),
    sa.Column('finish_spec', sa.String(length=256), nullable=True),
    sa.Column('defect_criteria', sa.Text(), nullable=True),
    sa.Column('supplier_notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.String(length=32), nullable=False),
    sa.Column('updated_at', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('process_card_id')
    )
    op.create_index('ix_qc_process_cards_project_id', 'qc_process_cards', ['project_id'], unique=False)

    op.create_table('qc_comparison_reports',
    sa.Column('report_id', sa.String(length=36), nullable=False),
    sa.Column('project_id', sa.String(length=36), nullable=False),
    sa.Column('milestone_id', sa.String(length=36), nullable=True),
    sa.Column('overall_result', sa.String(length=32), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('provider_name', sa.String(length=32), nullable=False),
    sa.Column('model_name', sa.String(length=64), nullable=False),
    sa.Column('requested_provider', sa.String(length=32), nullable=False),
    sa.Column('fallback_used', sa.Boolean(), nullable=False),
    sa.Column('m_side_feedback_zh', sa.Text(), nullable=False),
    sa.Column('m_side_feedback_en', sa.Text(), nullable=False),
    sa.Column('b_side_summary', sa.Text(), nullable=False),
    sa.Column('image_count', sa.Integer(), nullable=False),
    sa.Column('frames_used', sa.Integer(), nullable=False),
    sa.Column('buyer_confirmation_required', sa.Boolean(), nullable=False),
    sa.Column('saved_at', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index('ix_qc_comparison_reports_project_id', 'qc_comparison_reports', ['project_id'], unique=False)
    op.create_index('ix_qc_comparison_reports_milestone_id', 'qc_comparison_reports', ['milestone_id'], unique=False)

    op.create_index('ix_supplier_inquiries_project_id', 'supplier_inquiries', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_supplier_inquiries_project_id', table_name='supplier_inquiries')
    op.drop_index('ix_qc_comparison_reports_milestone_id', table_name='qc_comparison_reports')
    op.drop_index('ix_qc_comparison_reports_project_id', table_name='qc_comparison_reports')
    op.drop_table('qc_comparison_reports')
    op.drop_index('ix_qc_process_cards_project_id', table_name='qc_process_cards')
    op.drop_table('qc_process_cards')
    op.drop_index('ix_qc_reference_images_project_id', table_name='qc_reference_images')
    op.drop_table('qc_reference_images')
