from enum import Enum


class SegmentType(str, Enum):
    ENTITY = ('GL_ENTITY', 'entity_cd')
    DEPARTMENT = ('GL_DEPT', 'dept_cd')
    BRANCH = ('GL_BRANCH', 'branch_cd')
    ACCOUNT = ('GL_ACCOUNT', 'gl_account')
    SUB_ACCOUNT = ('GL_SUB_ACCOUNT', 'sub_account')
    AFFILIATE = ('GL_AFFILIATE', 'affiliate_cd')
    PRODUCT = ('GL_PRODUCT', 'product_cd')
    BOOK = ('GL_BOOK', 'book_cd')
    SOURCE = ('GL_SOURCE', 'source_cd')

    field_name: str

    def __new__(
        cls,
        value: str,
        field_name: str,
    ):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.field_name = field_name
        return obj
