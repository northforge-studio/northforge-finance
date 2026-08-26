from enum import StrEnum


class SegmentType(StrEnum):
    ENTITY = 'GL_ENTITY'
    DEPARTMENT = 'GL_DEPT'
    BRANCH = 'GL_BRANCH'
    ACCOUNT = 'GL_ACCOUNT'
    SUB_ACCOUNT = 'GL_SUB_ACCOUNT'
    AFFILIATE = 'GL_AFFILIATE'
    PRODUCT = 'GL_PRODUCT'
    BOOK = 'GL_BOOK'
    SOURCE = 'GL_SOURCE'
