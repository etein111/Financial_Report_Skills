"""report_maker scripts 包初始化文件。"""

from report_maker.scripts.neolyst_integration import (
    resolve_template_for_report,
    resolve_analysts_from_elements,
    get_contact_person_options,
    resolve_coverage_for_report,
    detect_language_from_title,
    compress_investment_thesis,
    map_elements_to_draft,
    save_draft,
    validate_draft,
    submit_draft,
    upload_draft_files,
    upload_model,
)

from report_maker.scripts.workflow import (
    prepare_and_save_draft,
    submit_report_workflow,
    is_company_report,
    is_sector_report,
    classify_report_type,
    COMPANY_REPORT_TYPES,
    SECTOR_REPORT_TYPES,
)
