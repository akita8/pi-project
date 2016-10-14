from .database import Base
from sqlalchemy import Column, Integer, String, Float, Date


class Stock(Base):
    __tablename__ = 'stock'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), unique=True)
    name = Column(String(50))
    threshold = Column(String(10))
    progress = Column(String(10))
    price = Column(Float())
    variation = Column(String(10))

    def __init__(self, symbol=None, name=None, threshold=None, progress=None,
                 price=None, variation=None):
        self.symbol = symbol
        self.name = name
        self.threshold = threshold
        self.progress = progress
        self.price = price
        self.variation = variation

    def __repr__(self):
        return '<Stock %r>' % (self.name)


class Bond_IT(Base):
    __tablename__ = 'bond_it'
    id = Column(Integer, primary_key=True)
    isin = Column(String(50), unique=True)
    name = Column(String(50))
    coupon = Column(Float())
    typology = Column(String(50))
    threshold = Column(String(10))
    progress = Column(String(10))
    price = Column(Float())
    max_y = Column(Float())
    min_y = Column(Float())
    yield_y = Column(Float())
    yield_tot = Column(Float())
    maturity = Column(Date())

    def __init__(self, isin=None, name=None, coupon=None, threshold=None,
                 progress=None, price=None, max_y=None, min_y=None,
                 yield_y=None, yield_tot=None, typology=None, maturity=None):
        self.isin = isin
        self.name = name
        self.threshold = threshold
        self.coupon = coupon
        self.typology = typology
        self.progress = progress
        self.price = price
        self.max_y = max_y
        self.min_y = min_y
        self.yield_y = yield_y
        self.yield_tot = yield_tot
        self.maturity = maturity

    def __repr__(self):
        return '<Bond_it %r>' % (self.name)


class Bond_TR(Base):
    __tablename__ = 'bond_tr'
    id = Column(Integer, primary_key=True)
    maturity = Column(Date(), unique=True)
    name = Column(String(50))
    coupon = Column(Float())
    threshold = Column(String(10))
    progress = Column(String(10))
    price = Column(Float())
    yield_y = Column(Float())
    yield_tot = Column(Float())

    def __init__(self, name=None, threshold=None, coupon=None, maturity=None,
                 progress=None, price=None, yield_y=None, yield_tot=None):
        self.maturity = maturity
        self.name = name
        self.threshold = threshold
        self.progress = progress
        self.price = price
        self.coupon = coupon
        self.yield_y = yield_y
        self.yield_tot = yield_tot

    def __repr__(self):
        return '<Bond_tr %r>' % (str(self.maturity))
