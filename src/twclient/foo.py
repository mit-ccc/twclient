# pylint: disable-all

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func

from twclient import models as md

engine = create_engine('postgresql:///')

Session = sessionmaker(bind=engine)
session = Session()

# tag = 'universe'
# tagged_users = session \
#     .query(md.UserTag.user_id) \
#     .join(md.Tag, md.Tag.tag_id == md.UserTag.tag_id) \
#     .filter(md.Tag.name == tag) \
#     .all()
# print(tagged_users)

# fg = session \
#     .query(md.Follow) \
#     .filter_by(valid_end_dt=None) \
#     .all()
# print(len(fg))
# print(fg[0])
#
# fg = [(r.source_user_id, r.target_user_id) for r in fg]
# print(len(fg))
# print(fg[0])

# mg = session \
#     .query(md.Tweet.user_id, md.UserMention.mentioned_user_id, func.count()) \
#     .join(md.Tweet, md.Tweet.tweet_id == md.UserMention.tweet_id) \
#     .group_by(md.Tweet.user_id, md.UserMention.mentioned_user_id) \
#     .all()
# print(len(mg))
# print(mg[0])

