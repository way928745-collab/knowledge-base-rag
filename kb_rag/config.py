"""配置加载。"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULT_DOMAIN_ORDER = [
    "enterprise",
    "product",
    "business",
    "marketing",
    "internal_policy",
    "technology",
    "legal",
    "faq",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "kb_path": "./kb-data",
    "collection_name": "knowledge_base",
    "embedding_model": "BAAI/bge-small-zh-v1.5",
    "chunking": {
        "small_max_chars": 1200,
        "small_overlap": 100,
        "large_max_chars": 3000,
        "large_overlap": 200,
        "small_domains": ["faq", "internal_policy"],
        "large_domains": ["product", "marketing", "technology", "legal", "enterprise"],
    },
    "domains": {
        "enterprise": {
            "label": "企业基础信息",
            "description": "企业概况、发展历程、组织架构、资质证书、企业文化、对外口径、联系方式",
            "keywords": ["公司", "企业", "集团", "组织架构", "发展历程", "资质", "企业文化", "简介", "联系方式"],
        },
        "product": {
            "label": "产品与服务",
            "description": "产品介绍、产品线、功能、参数、规格、版本差异、服务项目、交付标准、产品限制",
            "keywords": ["产品", "功能", "参数", "规格", "版本", "服务", "交付", "产品线", "用户手册"],
        },
        "business": {
            "label": "对外商务与政策",
            "description": "报价、付款、交付周期、质保、售后、退换货、投诉、合同模板、优惠政策",
            "keywords": ["报价", "价格", "付款", "质保", "售后", "退换", "合同", "优惠", "发票"],
        },
        "marketing": {
            "label": "营销与品牌素材",
            "description": "品牌话术、禁用词、案例、证言、宣传物料、公众号、白皮书、历史宣传资料",
            "keywords": ["品牌", "话术", "文案", "案例", "宣传", "营销", "广告", "海报", "公众号"],
        },
        "internal_policy": {
            "label": "内部管理制度",
            "description": "人事考勤、入职离职、报销、福利、招聘制度、行政办公、采购、资产、内部IT",
            "keywords": ["考勤", "入职", "离职", "报销", "福利", "招聘", "制度", "行政", "内部", "办公"],
        },
        "technology": {
            "label": "技术研发文档",
            "description": "技术白皮书、接口文档、运维手册、故障排查、产品原理、技术方案、研发文档",
            "keywords": ["接口", "API", "运维", "部署", "故障", "排查", "白皮书", "技术方案", "架构"],
        },
        "legal": {
            "label": "法务与风险合规",
            "description": "隐私政策、用户协议、合规要求、风险提示、禁止行为、法律责任",
            "keywords": ["隐私", "协议", "合规", "风险", "法律", "条款", "禁止", "责任"],
        },
        "faq": {
            "label": "FAQ与历史问答",
            "description": "客户高频问题与标准答案、员工高频问题、历史问答记录",
            "keywords": ["FAQ", "问答", "常见问题", "高频问题", "客服"],
        },
    },
    "auto_tags": {
        "usage_type": {
            "fact": ["报价", "参数", "规格", "政策", "制度", "规定", "标准", "流程"],
            "marketing": ["品牌", "话术", "案例", "宣传", "文案", "软文", "营销"],
            "policy": ["制度", "规定", "规范", "管理办法"],
            "faq": ["FAQ", "问答", "常见问题", "高频问题"],
        },
        "audience": {
            "external": ["对外", "客户", "用户", "访客", "公开"],
            "internal": ["内部", "员工", "人事", "制度", "办公", "报销", "行政"],
        },
        "security_level": {
            "公开": ["公开", "对外", "官网", "公示"],
            "内部": ["内部", "员工", "制度", "机密"],
            "机密": ["机密", "绝密", "保密", "未发布", "谈判", "成本", "隐私"],
        },
    },
    "date_patterns": [
        r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})",
        r"(\d{4})[-/年.](\d{1,2})",
    ],
    "version_pattern": r"[vV](\d+\.\d+(?:\.\d+)?)",
    "retrieval": {"default_top_k": 5},
}


def load(path: str | None = None) -> dict[str, Any]:
    if not path:
        return copy.deepcopy(DEFAULT_CONFIG)
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        user = yaml.safe_load(f) or {}
    merged = copy.deepcopy(DEFAULT_CONFIG)
    merged.update(user or {})
    if user and isinstance(user.get("domains"), dict):
        merged["domains"].update(user["domains"])
    if user and isinstance(user.get("chunking"), dict):
        merged["chunking"].update(user["chunking"])
    return merged