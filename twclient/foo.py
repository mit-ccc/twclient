from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models as md

engine = create_engine('postgresql:///test', echo=False)

md.Base.metadata.drop_all(engine)
md.Base.metadata.create_all(engine)

sessionfactory = sessionmaker()
sessionfactory.configure(bind=engine)
session = sessionfactory()

user = md.User(screen_name='barackobama')
session.add(user)

session.commit()

