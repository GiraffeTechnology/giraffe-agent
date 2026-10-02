"""Message templates for B-side and M-side AI Merchandiser communications."""

B_MILESTONE_REVIEW = (
    "Milestone confirmation required:\n"
    "The supplier uploaded {media_count} photo(s) for the {milestone_type} stage.\n"
    "Reply:\nA. Confirm\nB. Request more photos\nC. Raise issue"
)

B_LOGISTICS_UPDATE = (
    "Logistics update:\n"
    "Tracking number {tracking_number} ({carrier_name}) — status: {normalized_status}."
)

B_DELIVERY_SIGNOFF = (
    "The shipment ({tracking_number}) has been marked as delivered. "
    "Please confirm receipt:\n"
    "A. Confirm received\nB. Not received\nC. Received with issue"
)

B_EXCEPTION_OPTIONS = (
    "Exception: {exception_type}.\n"
    "Available options:\n{options_text}"
)

M_PROGRESS_CHECK = (
    "The order is confirmed. Please update progress for the {stage} stage. Reply:\n"
    "A. Completed\nB. In progress\nC. There is an issue; please explain"
)

M_MEDIA_UPLOAD = (
    "Please upload photos for the {milestone_type} stage: {media_desc}. Make them clear enough for the buyer to review."
)

M_LOGISTICS_HANDOVER = (
    "The order has reached logistics handover. Please provide the carrier and tracking number, and upload a shipping label photo.\n"
    "Example: Shipped via SF Express, tracking SF123456789, dispatched this afternoon."
)

M_MATERIAL_DELAY_RESPONSE = (
    "Please confirm whether to use the backup fabric or keep waiting for the original fabric. If delivery is affected, provide the revised expected completion time."
)


def render(template: str, **kwargs) -> str:
    return template.format(**kwargs)
