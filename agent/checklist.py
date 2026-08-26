"""
The compliance checklist the UKRP coordinator distributes to each node.

This is the ONLY thing that travels outward from the coordinator.
It contains no client data - it is a generic requirements list.

Scope for the demo: GB market access for Class I / IIa medical devices
under the Medical Devices Regulations 2002 (SI 2002 No 618, as amended).
"""

CHECKLIST = [
    {
        "id": "R01",
        "name_en": "Device description and specification",
        "name_zh": "产品描述与技术规格",
        "keywords": ["device description", "specification", "product spec",
                     "intended purpose", "variants"],
        "note": "Must cover models, variants, accessories, intended purpose.",
    },
    {
        "id": "R02",
        "name_en": "Labelling and IFU in English",
        "name_zh": "英文标签与使用说明书",
        "keywords": ["labelling", "labeling", "ifu", "instructions for use"],
        "note": "GB requires English. UKCA mark and UKRP address block.",
    },
    {
        "id": "R03",
        "name_en": "Essential requirements checklist",
        "name_zh": "基本要求对照表",
        "keywords": ["essential requirement", "annex i", "annex 1"],
        "note": "UK MDR 2002 Annex I. Not the EU MDR GSPR.",
    },
    {
        "id": "R04",
        "name_en": "Risk management file (ISO 14971)",
        "name_zh": "风险管理文件",
        "keywords": ["risk management", "14971", "risk file", "hazard"],
        "note": "Plan, analysis, controls, residual risk evaluation.",
    },
    {
        "id": "R05",
        "name_en": "Biological evaluation (ISO 10993)",
        "name_zh": "生物相容性评价",
        "keywords": ["biocompat", "biological evaluation", "10993"],
        "note": "Applies to body-contacting devices only.",
        "conditional": True,
    },
    {
        "id": "R06",
        "name_en": "Sterilisation validation",
        "name_zh": "灭菌确认",
        "keywords": ["sterilis", "steriliz", "11135", "17665", "ethylene oxide"],
        "note": "Applies to devices supplied sterile only.",
        "conditional": True,
    },
    {
        "id": "R07",
        "name_en": "Clinical evaluation report",
        "name_zh": "临床评价报告",
        "keywords": ["clinical evaluation", "cer", "clinical evidence"],
        "note": "Must be current and cover the stated intended purpose.",
    },
    {
        "id": "R08",
        "name_en": "QMS certificate (ISO 13485)",
        "name_zh": "质量管理体系证书",
        "keywords": ["13485", "quality management", "qms"],
        "note": "Scope must cover the device in question.",
    },
    {
        "id": "R09",
        "name_en": "Approved Body certificate",
        "name_zh": "英国指定机构证书",
        "keywords": ["approved body", "notified body", "conformity assessment"],
        "note": "Required for Class IIa and above. Not for Class I non-sterile.",
        "conditional": True,
    },
    {
        "id": "R10",
        "name_en": "Declaration of conformity",
        "name_zh": "符合性声明",
        "keywords": ["declaration of conformity", "doc"],
        "note": "Must cite UK MDR 2002, be signed and dated.",
    },
    {
        "id": "R11",
        "name_en": "UKRP designation",
        "name_zh": "英国责任人委任",
        "keywords": ["ukrp", "responsible person", "designation"],
        "note": "Letter of designation or signed UKRP agreement.",
    },
    {
        "id": "R12",
        "name_en": "Post-market surveillance plan",
        "name_zh": "上市后监督计划",
        "keywords": ["post-market", "post market", "pms", "vigilance"],
        "note": "Complaint handling, trending, MHRA vigilance route.",
    },
]

# Words in a document that suggest it exists but is not finished.
INCOMPLETE_MARKERS = [
    "draft", "to be completed", "tbd", "in progress", "unsigned",
    "not yet", "partial", "under review", "placeholder",
]

# Findings that indicate a document exists but cites the wrong regulation.
WRONG_REGULATION_MARKERS = [
    "2017/745", "eu mdr", "regulation (eu)",
]
