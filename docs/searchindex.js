Search.setIndex({docnames:["apidocs","index","overview/changelog","overview/license","overview/readme","vignettes/extract","vignettes/extracts/follow-graph","vignettes/extracts/mutual-followers-friends-counts","vignettes/extracts/tweet-graphs","vignettes/extracts/tweets","vignettes/extracts/user-info","vignettes/fetch"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["apidocs.rst","index.rst","overview/changelog.rst","overview/license.rst","overview/readme.rst","vignettes/extract.rst","vignettes/extracts/follow-graph.rst","vignettes/extracts/mutual-followers-friends-counts.rst","vignettes/extracts/tweet-graphs.rst","vignettes/extracts/tweets.rst","vignettes/extracts/user-info.rst","vignettes/fetch.rst"],objects:{"":[[0,0,0,"-","twclient"]],"twclient.authpool":[[0,1,1,"","AuthPoolAPI"]],"twclient.cli":[[0,2,1,"","cli"]],"twclient.error":[[0,3,1,"","BadSchemaError"],[0,3,1,"","BadTagError"],[0,3,1,"","BadTargetError"],[0,3,1,"","CapacityError"],[0,3,1,"","NotFoundError"],[0,3,1,"","ProtectedUserError"],[0,3,1,"","ReadFailureError"],[0,3,1,"","SemanticError"],[0,3,1,"","TWClientError"],[0,3,1,"","TwitterAPIError"],[0,3,1,"","TwitterLogicError"],[0,3,1,"","TwitterServiceError"],[0,2,1,"","dispatch_tweepy"]],"twclient.error.BadTagError":[[0,4,1,"","tag"]],"twclient.error.BadTargetError":[[0,4,1,"","targets"]],"twclient.error.CapacityError":[[0,5,1,"","tweepy_is_instance"]],"twclient.error.NotFoundError":[[0,5,1,"","tweepy_is_instance"]],"twclient.error.ProtectedUserError":[[0,5,1,"","tweepy_is_instance"]],"twclient.error.ReadFailureError":[[0,5,1,"","tweepy_is_instance"]],"twclient.error.TWClientError":[[0,4,1,"","exit_status"],[0,4,1,"","message"]],"twclient.error.TwitterAPIError":[[0,4,1,"","api_code"],[0,5,1,"","from_tweepy"],[0,6,1,"","http_code"],[0,4,1,"","response"],[0,5,1,"","tweepy_is_instance"]],"twclient.job":[[0,1,1,"","ApiJob"],[0,1,1,"","ApplyTagJob"],[0,1,1,"","CreateTagJob"],[0,1,1,"","DeleteTagJob"],[0,1,1,"","FollowGraphJob"],[0,1,1,"","FollowersJob"],[0,1,1,"","FriendsJob"],[0,1,1,"","InitializeJob"],[0,1,1,"","Job"],[0,1,1,"","TagJob"],[0,1,1,"","TargetJob"],[0,1,1,"","TweetsJob"],[0,1,1,"","UserInfoJob"]],"twclient.job.ApiJob":[[0,4,1,"","allow_api_errors"],[0,4,1,"","api"],[0,4,1,"","load_batch_size"],[0,5,1,"","validate_targets"]],"twclient.job.ApplyTagJob":[[0,4,1,"","resolve_mode"],[0,5,1,"","run"]],"twclient.job.CreateTagJob":[[0,5,1,"","run"]],"twclient.job.DeleteTagJob":[[0,5,1,"","run"]],"twclient.job.FollowGraphJob":[[0,6,1,"","direction"],[0,4,1,"","resolve_mode"],[0,5,1,"","run"]],"twclient.job.FollowersJob":[[0,4,1,"","direction"]],"twclient.job.FriendsJob":[[0,4,1,"","direction"]],"twclient.job.InitializeJob":[[0,5,1,"","run"]],"twclient.job.Job":[[0,4,1,"","engine"],[0,5,1,"","ensure_schema_version"],[0,5,1,"","get_or_create"],[0,5,1,"","run"],[0,4,1,"","session"]],"twclient.job.TagJob":[[0,4,1,"","tag"]],"twclient.job.TargetJob":[[0,4,1,"","allow_missing_targets"],[0,6,1,"","bad_targets"],[0,6,1,"","good_targets"],[0,6,1,"","missing_targets"],[0,6,1,"","resolve_mode"],[0,5,1,"","resolve_targets"],[0,6,1,"","resolved"],[0,4,1,"","targets"],[0,6,1,"","users"],[0,5,1,"","validate_targets"]],"twclient.job.TweetsJob":[[0,4,1,"","max_tweets"],[0,4,1,"","old_tweets"],[0,4,1,"","resolve_mode"],[0,5,1,"","run"],[0,4,1,"","since_timestamp"]],"twclient.job.UserInfoJob":[[0,4,1,"","resolve_mode"],[0,5,1,"","run"]],"twclient.models":[[0,1,1,"","Follow"],[0,1,1,"","FromTweepyInterface"],[0,1,1,"","Hashtag"],[0,1,1,"","HashtagMention"],[0,1,1,"","List"],[0,1,1,"","ListFromTweepyInterface"],[0,1,1,"","Media"],[0,1,1,"","MediaMention"],[0,1,1,"","MediaType"],[0,1,1,"","MediaVariant"],[0,1,1,"","SchemaVersion"],[0,1,1,"","StgFollow"],[0,1,1,"","Symbol"],[0,1,1,"","SymbolMention"],[0,1,1,"","Tag"],[0,1,1,"","TimestampsMixin"],[0,1,1,"","Tweet"],[0,1,1,"","UniqueMixin"],[0,1,1,"","Url"],[0,1,1,"","UrlMention"],[0,1,1,"","User"],[0,1,1,"","UserData"],[0,1,1,"","UserList"],[0,1,1,"","UserMention"],[0,1,1,"","UserTag"]],"twclient.models.Follow":[[0,4,1,"","follow_id"],[0,4,1,"","source_user_id"],[0,4,1,"","target_user_id"],[0,4,1,"","valid_end_dt"],[0,4,1,"","valid_start_dt"]],"twclient.models.FromTweepyInterface":[[0,5,1,"","from_tweepy"]],"twclient.models.Hashtag":[[0,4,1,"","hashtag_id"],[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","name"],[0,4,1,"","unique_hash"]],"twclient.models.HashtagMention":[[0,4,1,"","end_index"],[0,4,1,"","hashtag_id"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","modified_dt"],[0,4,1,"","start_index"],[0,4,1,"","tweet_id"]],"twclient.models.List":[[0,4,1,"","api_response"],[0,4,1,"","create_dt"],[0,4,1,"","description"],[0,4,1,"","display_name"],[0,5,1,"","from_tweepy"],[0,4,1,"","full_name"],[0,4,1,"","insert_dt"],[0,4,1,"","list_id"],[0,4,1,"","member_count"],[0,4,1,"","mode"],[0,4,1,"","modified_dt"],[0,4,1,"","slug"],[0,4,1,"","subscriber_count"],[0,4,1,"","uri"],[0,4,1,"","user_id"]],"twclient.models.ListFromTweepyInterface":[[0,5,1,"","list_from_tweepy"]],"twclient.models.Media":[[0,4,1,"","aspect_ratio_height"],[0,4,1,"","aspect_ratio_width"],[0,4,1,"","duration"],[0,5,1,"","from_tweepy"],[0,4,1,"","insert_dt"],[0,4,1,"","media_id"],[0,4,1,"","media_type_id"],[0,4,1,"","media_url_id"],[0,4,1,"","modified_dt"]],"twclient.models.MediaMention":[[0,4,1,"","end_index"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","media_id"],[0,4,1,"","modified_dt"],[0,4,1,"","start_index"],[0,4,1,"","tweet_id"],[0,4,1,"","twitter_display_url"],[0,4,1,"","twitter_expanded_url"],[0,4,1,"","twitter_short_url"]],"twclient.models.MediaType":[[0,5,1,"","from_tweepy"],[0,4,1,"","insert_dt"],[0,4,1,"","media_type_id"],[0,4,1,"","modified_dt"],[0,4,1,"","name"],[0,4,1,"","unique_hash"]],"twclient.models.MediaVariant":[[0,4,1,"","bitrate"],[0,4,1,"","content_type"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","media_id"],[0,4,1,"","modified_dt"],[0,4,1,"","url_id"]],"twclient.models.SchemaVersion":[[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","version"]],"twclient.models.Symbol":[[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","name"],[0,4,1,"","symbol_id"],[0,4,1,"","unique_hash"]],"twclient.models.SymbolMention":[[0,4,1,"","end_index"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","modified_dt"],[0,4,1,"","start_index"],[0,4,1,"","symbol_id"],[0,4,1,"","tweet_id"]],"twclient.models.Tag":[[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","name"],[0,4,1,"","tag_id"]],"twclient.models.Tweet":[[0,4,1,"","api_response"],[0,4,1,"","content"],[0,4,1,"","create_dt"],[0,4,1,"","favorite_count"],[0,5,1,"","from_tweepy"],[0,4,1,"","in_reply_to_status_id"],[0,4,1,"","in_reply_to_user_id"],[0,4,1,"","insert_dt"],[0,4,1,"","lang"],[0,4,1,"","modified_dt"],[0,4,1,"","quoted_status_id"],[0,4,1,"","retweet_count"],[0,4,1,"","retweeted_status_id"],[0,4,1,"","source"],[0,4,1,"","truncated"],[0,4,1,"","tweet_id"],[0,4,1,"","user_id"]],"twclient.models.UniqueMixin":[[0,5,1,"","as_unique"]],"twclient.models.Url":[[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","unique_hash"],[0,4,1,"","url"],[0,4,1,"","url_id"]],"twclient.models.UrlMention":[[0,4,1,"","description"],[0,4,1,"","end_index"],[0,4,1,"","expanded_short_url"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","modified_dt"],[0,4,1,"","start_index"],[0,4,1,"","status"],[0,4,1,"","title"],[0,4,1,"","tweet_id"],[0,4,1,"","twitter_display_url"],[0,4,1,"","twitter_short_url"],[0,4,1,"","url_id"]],"twclient.models.User":[[0,5,1,"","from_tweepy"],[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","user_id"]],"twclient.models.UserData":[[0,4,1,"","api_response"],[0,4,1,"","create_dt"],[0,4,1,"","description"],[0,4,1,"","display_name"],[0,4,1,"","followers_count"],[0,4,1,"","friends_count"],[0,5,1,"","from_tweepy"],[0,4,1,"","insert_dt"],[0,4,1,"","listed_count"],[0,4,1,"","location"],[0,4,1,"","modified_dt"],[0,4,1,"","protected"],[0,4,1,"","screen_name"],[0,4,1,"","url_id"],[0,4,1,"","user_data_id"],[0,4,1,"","user_id"],[0,4,1,"","verified"]],"twclient.models.UserList":[[0,4,1,"","list_id"],[0,4,1,"","user_id"],[0,4,1,"","user_list_id"],[0,4,1,"","valid_end_dt"],[0,4,1,"","valid_start_dt"]],"twclient.models.UserMention":[[0,4,1,"","end_index"],[0,4,1,"","insert_dt"],[0,5,1,"","list_from_tweepy"],[0,4,1,"","mentioned_user_id"],[0,4,1,"","modified_dt"],[0,4,1,"","start_index"],[0,4,1,"","tweet_id"]],"twclient.models.UserTag":[[0,4,1,"","insert_dt"],[0,4,1,"","modified_dt"],[0,4,1,"","tag_id"],[0,4,1,"","user_id"],[0,4,1,"","user_tag_id"]],"twclient.target":[[0,1,1,"","ScreenNameTarget"],[0,1,1,"","SelectTagTarget"],[0,1,1,"","Target"],[0,1,1,"","TwitterListTarget"],[0,1,1,"","UserIdTarget"]],"twclient.target.ScreenNameTarget":[[0,4,1,"","allowed_resolve_modes"],[0,5,1,"","resolve"]],"twclient.target.SelectTagTarget":[[0,4,1,"","allowed_resolve_modes"],[0,5,1,"","resolve"]],"twclient.target.Target":[[0,6,1,"","allowed_resolve_modes"],[0,6,1,"","bad_targets"],[0,6,1,"","context"],[0,6,1,"","good_targets"],[0,6,1,"","missing_targets"],[0,4,1,"","randomize"],[0,5,1,"","resolve"],[0,6,1,"","resolved"],[0,4,1,"","targets"],[0,6,1,"","users"]],"twclient.target.TwitterListTarget":[[0,4,1,"","allowed_resolve_modes"],[0,5,1,"","resolve"]],"twclient.target.UserIdTarget":[[0,4,1,"","allowed_resolve_modes"],[0,5,1,"","resolve"]],"twclient.twitter_api":[[0,1,1,"","TwitterApi"]],"twclient.twitter_api.TwitterApi":[[0,4,1,"","auths"],[0,5,1,"","followers_ids"],[0,5,1,"","friends_ids"],[0,5,1,"","get_list"],[0,5,1,"","list_members"],[0,5,1,"","lookup_users"],[0,5,1,"","make_api_call"],[0,4,1,"","pool"],[0,5,1,"","user_timeline"]],twclient:[[0,0,0,"-","authpool"],[0,0,0,"-","cli"],[0,0,0,"-","error"],[0,0,0,"-","job"],[0,0,0,"-","models"],[0,0,0,"-","target"],[0,0,0,"-","twitter_api"]]},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","function","Python function"],"3":["py","exception","Python exception"],"4":["py","attribute","Python attribute"],"5":["py","method","Python method"],"6":["py","property","Python property"]},objtypes:{"0":"py:module","1":"py:class","2":"py:function","3":"py:exception","4":"py:attribute","5":"py:method","6":"py:property"},terms:{"0":[10,11],"01":9,"03":[],"05":[],"06":9,"1":[7,8,10],"123":7,"13":[],"14":[],"140":0,"14624234":11,"16":0,"172409353":11,"1725438692309":11,"182359253":11,"1825471204":11,"185239864":11,"1853209475":11,"2":[0,2,6,7,8,11],"2019":3,"2020":9,"2021":3,"23965249864":11,"28723520928":11,"3200":0,"39702507914":11,"4382530952834":11,"456":7,"5000":[0,11],"6":6,"789":[],"9":0,"abstract":0,"boolean":0,"case":[0,9,11],"catch":0,"class":[0,2,11],"default":[0,11],"do":[0,3,7,11],"final":[0,6,7,9,11],"float":0,"function":0,"import":[6,9,11],"int":[0,10],"long":0,"new":[0,6,10,11],"null":[0,6,7,9,10],"public":0,"return":[0,6,7,8,9,11],"short":[0,9],"static":0,"switch":[0,11],"true":[0,6],"while":[0,9,11],A:[0,2,3,6,7,9],AND:3,AS:3,And:[7,9,11],As:[0,6,9,11],At:0,BE:3,BUT:3,Be:11,But:[0,6,7,11],By:7,FOR:3,For:[0,6,11],IN:3,IS:3,If:[0,7,11],In:[0,6,11],Is:0,It:[0,6,7,9,11],NO:3,NOT:3,No:[0,11],Not:[0,7],OF:3,OR:3,One:[6,7,9],Such:0,THE:3,TO:3,That:[0,6,7,11],The:[0,2,4,5,6,7,11],There:[0,7,11],These:[0,5,9],To:7,WITH:3,With:11,_:11,__:[],__init__:0,abc:0,abl:0,abort:[0,11],about:[0,4,5,7],abov:[3,6,7,11],accept:[0,11],access:[0,2,11],accord:[0,11],accordingli:[7,9],account:[0,11],account_create_dt:10,accumul:11,achiev:9,acquir:[5,11],across:0,action:3,actual:0,ad:[0,4,11],adapt:5,add:[0,4,7,11],addit:[0,11],address:0,ado:6,advantag:11,affect:6,after:[0,4],again:[0,6,7,11],against:0,ago:6,alia:11,all:[0,2,3,4,5,6,7,9],allow:[0,6,11],allow_api_error:0,allow_missing_target:0,allow_missing_us:0,allowed_resolve_mod:0,along:7,alreadi:[0,11],also:[0,4,6,7,8,11],alwai:0,amazon:11,among:[6,11],amount:[0,11],an:[0,3,4,6,7,8,9,11],analogu:0,analysi:[0,2,4,9,11],analyt:0,analyz:[5,11],android:[0,9,10],android_us:10,ani:[0,3,4,5,11],anoth:[0,6,7,9],anyth:[0,11],api:[1,2,4,5,8,9],api_cod:0,api_respons:0,apijob:0,app:[0,2,9,10,11],appealingli:9,appear:[0,7],append:10,appli:[0,4,11],applic:[0,11],applytagjob:0,appropri:0,approxim:0,apt:11,ar:[0,2,4,6,7,9,11],arbitrari:[0,2,11],arbitrarili:[4,7,11],aren:[5,9],argument:[0,7],aris:[3,7],around:[0,11],as_uniqu:0,ask:[6,7,11],aspect:0,aspect_ratio_height:0,aspect_ratio_width:0,assign:0,associ:[0,3,11],assum:11,attempt:0,attribut:0,attributeerror:0,auth:0,authent:[2,11],authhandl:0,author:3,authpoolapi:0,autodetect:9,autoincr:0,autom:2,automat:[6,7,8,9],avail:0,avoid:[0,4,11],aw:11,awar:11,b:[0,6,7,11],back:[0,8,9,11],backend:[2,11],bad:0,bad_target:0,badschemaerror:0,badtagerror:0,badtargeterror:0,bare:11,base:[0,2,5,11],bash:11,basic:4,batch:[0,11],bearer:11,becaus:[0,6,7,11],been:[0,4,6,11],befor:[0,11],behavior:0,being:[0,11],bell:9,below:11,between:[6,7,11],big:7,bin:11,bio:[0,5],bit:[0,11],bitrat:0,bodi:0,bool:0,both:[0,2,6,11],brief:11,built:11,business_app_us:10,calcul:[0,7],call:[0,10,11],can:[0,2,4,5,6,7,8,9,11],candid:0,cannot:0,capabl:0,capac:0,capacity_retri:0,capacity_sleep:0,capacityerror:0,cashtag:[0,11],cat:11,caught:0,caus:[0,11],ceas:0,certain:[0,5,6,9],chain:0,chang:[0,2,6,7],changelog:1,charact:0,charg:3,check:[0,2],choic:11,choos:[5,11],cl:0,claim:3,classmethod:0,claus:[6,7,9],click:0,client:[0,4,9,10,11],cnt:7,co:0,coalesc:10,code:[0,9,11],collect:2,column:[0,6,7,9,11],com:[0,11],combin:[0,7],come:[8,11],command:[0,2,4,11],common:[0,5,7],commonli:5,commun:0,compat:0,complex:11,compli:11,complic:[6,7],compon:9,comput:[7,11],concaten:7,concern:5,condit:[0,3,6],config:[4,11],configur:[0,4,11],confirm:11,congress:[0,11],congression:0,connect:[0,3,11],consequ:0,consid:[0,7],consist:[0,6,11],constraint:[0,9],construct:0,consum:[0,4,11],contain:0,content:[0,5,9],content_typ:0,context:0,continu:[0,11],contract:3,control:0,conveni:2,convert:0,copi:[3,6],copyright:3,correct:[0,2],correctli:0,correl:7,correspond:[0,7],corrupt:0,cost:0,could:[0,9,11],count:[0,7,8,10],cours:[9,11],cover:5,creat:[0,4,6,7,8,9,11],create_dt:[0,8,9,10],createtagjob:0,creation:0,creativ:11,credenti:[0,4,11],cross:5,crude:0,cspan:[0,11],csv:11,cte:9,current:[0,5,6,7],cursor:[0,5,11],d:11,damag:3,data:[0,1,2,4,6,7,9],databas:[0,2,4,5,6,9],dataset:11,date:[0,6],db:[0,4,11],dbm:[5,7,11],dbmss:11,deal:3,debian:11,decl_api:0,declar:0,decoupl:5,dedic:0,dedup:0,dedupl:[0,7],defaut:0,defer:0,defin:[0,8,11],degre:11,deleg:0,delet:0,deletetagjob:0,depend:[0,8],deriv:[5,11],desc:10,descend:0,describ:6,descript:0,desktop:[0,9],desktop_us:10,destin:0,detail:[0,2,4,11],detect:0,determin:0,develop:11,dialect:[5,9],differ:[0,11],direct:[0,5,6],directli:11,discard:0,disclaim:11,discuss:[0,5,9,11],disk:11,dispatch:0,dispatch_tweepi:0,displai:0,display_nam:0,disposit:0,disrespect:11,distribut:[3,11],disucss:7,doc:11,docker:11,document:[2,3,11],doe:[0,5,6,11],doesn:[0,5,8,11],domain:0,don:[5,6,9,11],done:0,down:11,download:11,driver:11,drop:[0,4,11],duplic:0,durat:0,dure:[0,6],e:[0,8,11],each:[0,6,7,10,11],eas:[4,11],easi:[2,5,11],easier:[0,5,11],easili:6,edg:[0,2,6,7,11],effect:0,effici:0,either:[0,6,11],element:7,els:[0,9,11],empti:0,en:11,encapsul:0,encount:0,end:[0,6,9,11],end_index:0,endpoint:[0,11],engin:[0,11],enorm:11,enough:[0,11],ensur:[0,2,6],ensure_schema_vers:0,enter:0,entir:0,entiti:[0,2],entrypoint:0,equijoin:[],error:11,esp:[],especi:7,etc:[0,5,11],evalu:0,even:[0,9,11],event:3,eventu:0,everi:7,everyon:11,ex:0,exactli:0,exampl:[0,4,6,7,8,9,11],exc:0,excel:11,except:0,execut:[0,7],exist:[0,4,6,11],exit:0,exit_statu:0,expanded_short_url:0,expect:0,experi:6,expir:[6,7],explain:6,explan:6,expos:0,express:[0,3],extend:0,extens:[0,2,11],extract:[0,2,5,8,9,11],extrem:11,fact:[0,11],fail:0,fals:0,famili:11,faster:11,favorit:0,favorite_count:[0,9],featur:[4,6,7,11],fed:7,feed:11,fetch:[0,1,2,4,6,7,9,10],few:[9,11],field:[0,8,9],file:[0,3,4,9,11],filter:9,find:7,fire:11,first:[0,2,6,7,9,11],first_tweet_dt:10,fit:3,fix:9,flag:11,fo:[6,7,10],focu:4,focus:0,follow:[0,2,3,4,5,9,10],follow_id:0,followers_count:0,followers_id:0,followersjob:0,followgraphjob:0,foobar:11,foreign:[0,6,9],form:[0,11],format:[0,2,6,9,11],found:[0,6],four:11,free:[0,3],freeform:9,friend:[0,4,5,10,11],friendli:11,friends_count:0,friends_id:0,friendsjob:0,from:[0,1,3,5,6,7,8,9,10],from_tweepi:0,fromtweepyinterfac:0,fulfil:0,full:[0,9,11],full_nam:0,fulli:11,fun:11,fundament:5,furnish:3,further:[0,2,6],futur:0,g:[0,4,8,9,11],gave:0,gener:[0,5,7,11],get:[0,1,4,6,7,9],get_list:0,get_or_cr:0,give:[0,6,9,11],given:[0,7,11],go:[5,7,9],goal:4,goe:0,good:[0,11],good_target:0,gotten:11,grant:3,graph:[0,2,5,7,9],greater:[0,2],greatli:6,group:[2,7,8,10,11],h:11,ha:[0,6,7,11],had:6,handl:[0,4,6,11],hard:[5,7,9,11],hash:0,hashtag:[0,2,11],hashtag_id:0,hashtagment:0,have:[0,4,5,6,7,9,11],header:11,help:[0,4,11],here:[0,2,5,6,9,10,11],herebi:3,high:[0,4],higher:[0,4],histor:0,hit:[0,11],holder:3,homebrew:11,hook:0,hootsuit:10,housekeep:0,how:[0,5,6,7,8,9,11],howev:11,http:[0,11],http_code:0,hub:11,human:11,hundr:0,hydrat:0,i:[0,8,10],id:[0,7,9,11],identifi:0,ignor:[0,11],illustr:7,implement:[0,7,11],impli:3,in_reply_to_status_cont:9,in_reply_to_status_id:[0,9],in_reply_to_user_id:[0,8],inc:10,includ:[0,3,7,9],incompat:0,independ:2,index:[0,1],indic:[0,6,7,11],individu:11,info:[2,4,11],inform:[0,5,7,11],ingest:[0,2],initi:[0,4,11],initializejob:0,inner:[6,7,8,9,10],innermost:7,input:0,insert:[0,9],insert_dt:[0,10],instal:11,instanc:[0,5],instanti:0,instead:[0,11],institut:3,integ:0,intend:0,interact:11,interfac:[0,2,11],interpret:0,interrupt:0,intersect:7,interv:6,intimid:11,invok:11,involv:0,io:10,ios_us:10,ipad:10,iphon:[0,9,10],is_quote_tweet:9,is_repli:9,is_retweet:9,isn:[5,6,8],issu:[4,9],item:0,iter:7,its:[0,6,11],itself:[0,9,11],j:11,job:11,join:[6,7,8,9,10],jointli:0,journalist:[0,11],jq:11,json:[0,11],just:[0,5,6,7,8,9,11],keep:[2,11],kei:[0,4,6,9,11],kept:6,keyword:0,kind:[0,3,5],know:[0,7],kwarg:0,l:[4,11],lang:[0,9],languag:[0,9],larg:[0,6,7,11],larger:[0,7],last:[0,6],last_tweet_dt:10,later:[0,4,6,11],latter:[0,6],lead:0,leap:7,least:[0,5,11],leav:[0,9],led:0,left:[0,9,10,11],length:0,less:11,lesser:11,let:[7,9,11],level:[0,4,5,11],leverag:6,liabil:3,liabl:3,licens:1,lifetim:0,lightweight:11,like:[0,2,6,7,9,11],limit:[0,3,4,5,11],line:[0,2,4,11],link:0,linux:11,list:[0,2,4,6,7,11],list_from_tweepi:0,list_id:0,list_memb:0,listed_count:[0,10],listfromtweepyinterfac:0,liter:11,littl:11,ll:[5,7,11],load:[0,2,4,5,11],load_batch_s:0,local:[5,11],locat:[0,5],log:0,logic:0,longer:[0,9],look:[0,7],lookup:0,lookup_us:0,lot:[],low:[0,11],lower:0,ly:0,mac:[10,11],made:0,mai:[0,5,7,9,11],main:0,make:[0,2,5,11],make_api_cal:0,manag:11,mani:[0,2,4,7,11],manual:11,mark:[6,7],massachusett:3,max:10,max_item:0,max_tweet:0,me:11,mean:[0,5,7,11],media:[0,10],media_id:0,media_type_id:0,media_url_id:0,mediament:0,mediatyp:0,mediavari:0,member:[0,11],member_count:0,membership:[0,2],memori:[0,11],mention:[0,2,5,9,11],mentioned_user_id:[0,8],merchant:3,merg:[0,3],messag:0,meta:0,method:0,might:[0,7,9,11],migrat:0,mime:0,min:10,minim:[0,6],miss:[0,6],missing_target:0,mit:4,mix:11,mixin:0,mode:0,model:[2,11],modif:[0,9],modifi:[0,3],modified_dt:0,monitor:11,month:[6,8],more:[0,2,5,6,7,9,11],most:[0,5,6,10],mt:8,much:[],multipl:[0,4,11],multiplex:0,mung:11,must:0,mutabl:0,mutual:5,mutual_follow:7,mutual_friend:7,mysql:11,n:[4,7,9,11],name:[0,6,7,8,9,10,11],necessari:7,need:[0,4,6,7,8,9,11],neither:11,network:[0,6,9],newer:0,newest:0,newli:0,newlin:9,next:[0,11],non:0,none:0,nonexist:[0,11],noninfring:3,normal:[0,2,4,11],notabl:2,note:[0,6,7,9,11],noteworthi:11,notfounderror:0,noth:[0,5],notic:3,notimplementederror:0,notion:0,now:[0,6,7,11],nr:[],num:8,num_ment:8,num_repli:8,number:[0,6,7],numer:[0,11],nyt:11,nytim:11,o:7,oauth:11,obj:0,object:[0,2,9,11],obligatori:11,observ:[0,6],obsolet:6,obtain:3,obviou:[6,9],occur:0,offer:4,old_tweet:0,older:0,omit:11,onc:[0,7,11],one:[0,5,6,7,10,11],onli:[0,2,4,5,6,7,9,10,11],oper:[0,11],opposit:[0,7,11],option:[0,11],oracl:11,order:[0,7,10],org:11,organ:11,origin:0,orm:0,other:[0,3,6,9,11],otherwis:[0,3],our:11,out:[0,3,4,6,9,11],output:11,over:[0,2,7,9,10,11],overlap:8,overrid:0,own:[0,11],owner_id:0,owner_screen_nam:0,p:11,packag:[0,4,5,11],page:0,pagin:[5,11],pair:7,paramet:0,pars:[0,11],part:11,particular:[0,3,5,6,11],particularli:11,partit:10,partwai:0,pass:0,passwordless:11,past:6,pend:0,peopl:[6,11],per:0,period:[0,9],permiss:3,permit:3,persist:[0,4,11],person:3,photo:0,pick:7,piec:[5,6,11],pipe:11,place:[0,5],planner:[],platform:0,plugin:11,point:[5,6],pool:0,popul:[0,11],portion:3,posit:[0,11],possibl:0,post:[0,9,11],postgr:[4,9,11],postgresql:[4,5,11],posting_us:0,powertrack:11,practic:0,prefix:0,prepend:0,present:[0,5],preserv:0,previou:0,previous:[0,7],primari:[0,11],primit:4,print:11,privaci:11,privat:0,probabl:0,problem:0,process:[0,2,4,11],produc:11,profil:[0,4,11],program:0,progress:11,project:2,properti:0,protect:[0,10,11],protectedusererror:0,provid:[0,3,4,5,6,7,11],proxi:0,psql:11,publish:3,pull:4,purpos:3,put:5,pypi:11,python:11,qt:9,queri:[0,4,5,6,7,9,11],question:7,quick:9,quit:[0,7,11],quot:[0,5,6,7,9,11],quoted_status_cont:9,quoted_status_id:[0,8,9],r:9,rais:0,random:0,rate:[0,4,5,11],rather:[0,7,11],ratio:0,raw:[0,4,11],rd:11,re:[0,7,9,11],read:[0,11],readabl:11,readfailureerror:0,readm:1,real:0,reason:[0,5,7],receiv:[0,9,11],recent:[0,6,10],recommend:6,record:[0,6,9,11],reduc:0,refer:[0,7,11],referenc:[5,9],reflect:[0,9],refollow:6,regardless:11,regexp_replac:9,regular:[0,11],regularli:6,rel:0,relat:[2,5],relationship:[0,6],relev:11,reli:[0,7],remain:0,rememb:9,remind:11,render:0,repeat:6,repeatedli:4,replac:[0,11],repli:[0,2,5,9,11],repres:0,request:[0,11],requir:[0,6,7],research:4,reserv:[6,7,8,9],resolv:0,resolve_mod:0,resolve_target:0,resourc:0,respect:[0,11],respons:[0,4,8,11],rest:[5,7,11],restrict:[3,7],result:[0,7,11],resultset:7,retain:0,retri:0,retriev:[0,7,9,11],retweet:[0,2,5,9,11],retweet_count:[0,9],retweeted_status_cont:9,retweeted_status_id:[0,8,9],revers:[0,7],right:[3,11],rise:[0,9],rn:10,roll:0,roughli:[],row:[0,6,7,10],row_numb:10,rt:[0,9],run:[0,5,7,11],runtim:11,s:[0,5,6,7,9,11],safe:0,sai:[6,7,9,11],same:[0,11],sampl:11,sane:0,saniti:2,save:[4,11],scd:[0,2,6,11],schema:[0,4,11],schemavers:0,scrape:11,screen:[0,11],screen_nam:[0,10,11],screennametarget:0,script:[0,11],seamlessli:[4,11],searchabl:0,second:[0,9],secret:[4,11],see:[0,6,7,9,11],seen:11,select:[0,6,7,8,9,10,11],selecttagtarget:0,self:[0,9],sell:3,semant:2,semanticerror:0,send:0,sensibl:0,separ:[0,5,11],sequenti:0,seri:5,serial:11,server:6,servic:[0,11],session:0,set:[0,4,6,7,9,11],setup:4,seven:6,sever:[0,7],shall:3,shape:6,shell:11,shorten:0,should:[0,6,11],show:[0,11],shown:4,sign:0,signific:0,similar:7,similarli:[4,11],simpl:[6,7,9,11],simpler:11,simplest:9,simplifi:0,simultan:0,since_id:0,since_timestamp:0,site:6,situat:9,six:6,size:[0,11],skip:[0,11],slash:[0,11],sleep:0,slightli:6,slow:[0,7],slower:0,slowli:6,slug:[0,11],smaller:9,smart:[],smartphon:0,snapshot:11,snippet:6,so:[0,3,6,7,11],socialflow:10,socialmachin:4,socket:11,softwar:3,some:[0,4,5,6,7,9,11],someth:[0,11],sometim:[0,7],somewher:0,sort:5,sound:[6,11],sourc:[0,9,10,11],source_collaps:9,source_us:0,source_user_id:[0,6,7,8,10],space:[0,6,11],special:0,specif:[0,7,11],specifi:[0,6,11],speed:0,sql:[6,7,8,9,11],sqlalchemi:[0,2,11],sqlite:11,stabl:[0,2],stage:0,standard:[6,7,8,9],start:[0,6,11],start_index:0,state:[0,6],statist:0,statu:[0,8],status:[0,9],step:11,stgfollow:0,still:[0,6,9],stock:0,stop:0,storag:6,store:[0,4,6,11],str:0,straightforward:[],string:0,structur:9,stub:0,studio:10,stuff:[9,11],subclass:0,subcommand:11,subject:[3,4],sublicens:3,subqueri:7,subscrib:0,subscriber_count:0,subsequ:[0,6],subset:7,substanti:3,successfulli:0,summari:11,support:[0,2,5,11],suppos:0,sure:0,surplu:0,survey_respondents_2020:0,suspend:0,swap:7,sy:0,symbol:0,symbol_id:0,symbolment:0,syntax:5,system:11,t:[0,5,6,8,9,11],ta:[6,7,8,9,10],tabl:[0,6,7,8,9,10,11],tada:11,tag:[0,2,4,6,7,8,9,10],tag_id:[0,6,7,8,9,10],tagjob:0,tail:11,take:[0,11],talk:11,target:11,target_us:0,target_user_id:[0,6,7,8,10],targetjob:0,task:11,technolog:3,tell:[0,11],temporari:9,temporarili:0,term:[0,7,11],test1234:11,test:11,text:[0,9,11],tfo:10,tfr:10,than:[0,4,5,6,7,11],thank:0,thei:[0,5,6,7,11],them:[0,4,7,8,9,11],themselv:[0,7],theta:[],thi:[0,2,3,4,5,6,7,8,9,10,11],thing:[0,7,9,11],think:11,those:[0,6,7,9,11],though:[0,7,9,11],three:0,through:[0,11],throughout:7,thu:5,thumbnail:0,ticker:0,time:[0,2,4,6,8,9,11],timelin:0,timestamp:0,timestampsmixin:0,titl:0,tmp_follower_count:10,tmp_friend_count:10,tmp_tweet_data:10,tmp_univers:[6,7,8,9,10],tmp_user_data:10,togeth:0,token:[4,11],too:7,tool:[4,11],top:0,tort:3,total:9,track:[0,2,11],trade:11,transact:0,transpar:0,treat:0,treatment:0,trick:11,trigger:0,troubl:5,truncat:0,trust:11,ttd:10,tu:[9,10],tud:10,turn:0,tw:[8,9,10],twclient:[5,6,11],twclienterror:0,twclientrc:11,tweeperror:0,tweepi:[0,4,11],tweepy_is_inst:0,tweet:[0,2,4,5,6,10],tweet_create_dt:[],tweet_id:[0,8,9],tweetbot:10,tweetdeck:[9,10],tweets_all_tim:10,tweetsjob:0,twice:[],twitter1:[4,11],twitter2:[4,11],twitter:[0,1,2,4,5,6,7,8,9,10],twitter_display_url:0,twitter_expanded_url:0,twitter_list:11,twitter_short_url:0,twitter_us:11,twitterapi:0,twitterapierror:0,twitterlisttarget:0,twitterlogicerror:0,twitterserviceerror:0,two:[0,4,6,7,11],twp:9,twq:9,twr:9,twt:8,twurl:[4,11],type:[0,2,4,6,11],u:[4,6,7,8,9,10,11],ud:10,ultim:[0,8],unavail:0,under:11,underli:[0,11],understand:11,unfollow:[6,7],union:0,uniqu:[0,7],unique_hash:0,uniquemixin:0,univers:[6,7,8,9,10,11],unix:[0,11],unless:0,unlik:0,unstandard:9,unsupport:0,up:[0,4,7,11],updat:[0,6],uri:0,url:[0,4,5,11],url_id:0,urlment:0,us:[0,3,4,5,6,7,8,9,10,11],usabl:[0,11],usag:[0,4],user1:11,user2:11,user3:11,user:[0,2,4,5,6,7,8],user_data:[0,10],user_data_id:0,user_id1:7,user_id2:7,user_id:[0,6,7,8,9,10,11],user_list:11,user_list_id:0,user_ment:8,user_tag:[0,6,7,8,9,10],user_tag_id:0,user_timelin:0,userdata:0,useridtarget:0,userinfojob:0,userlist:0,userment:0,users_altern:11,usertag:0,usual:[0,4,9],ut1:7,ut2:7,ut:[6,7,8,9,10],utt:[6,8],v2:11,v:11,valid:[0,6,7],valid_end_dt:[0,6,7,10],valid_start_dt:[0,6],validate_target:0,valu:[0,7,11],varieti:2,variou:[0,7],ve:[7,11],verbos:11,veri:0,verifi:[0,10],version:[0,2,6,7,9],via:[0,2,11],video:0,view:[0,11],viewer:0,vignett:[5,6,7,9,11],visibl:0,wa:[0,6,9],wai:[0,7,11],walk:11,want:[0,4,5,7,9,10,11],warn:0,warranti:3,wasn:11,we:[0,5,6,7,9,10,11],web:[0,9,10],websit:[0,11],well:0,went:0,were:[0,6],what:[0,7,9],whatev:[0,5,11],whch:6,when:[0,6,7,8,9],where:[0,6,7,8,9,10],whether:[0,3,11],which:[0,6,7,9,11],whistl:9,who:[0,4,9,11],whom:3,whose:0,why:[5,11],within:[0,9],without:[0,3,4,6,11],won:11,work:[0,1,9,11],worri:[4,5],worth:[6,9],would:[0,7],wrap:0,wrapper:0,write:[5,11],wrong:0,wwbrannon:[4,11],www:11,x:7,xarg:11,xe:11,xxxxx:[4,11],xxxxxx:[4,11],y:[4,11],year:8,yet:11,yield:0,you:[4,5,6,7,9,11],your:[6,11]},titles:["API Documentation","Twclient Documentation","Changelog","License","README","Working with fetched data","Follow Graph","Mutual Followers and Friends","Tweet-Derived Graphs: Mention, Reply, Retweet, Quote","Users\u2019 Tweets","User-Level Information: Bio, Location, Etc.","Getting data from the Twitter API"],titleterms:{A:11,The:3,about:11,actual:11,ad:2,all:11,api:[0,11],authpool:0,bio:10,changelog:2,cli:0,data:[5,11],databas:11,deriv:8,document:[0,1],error:0,etc:10,exampl:5,extract:[],fetch:[5,11],follow:[6,7,11],friend:7,from:11,get:11,graph:[6,8,11],hydrat:11,identifi:11,indic:1,info:[],inform:10,introduct:11,job:0,level:10,licens:3,locat:10,mention:8,mit:3,model:0,mutual:7,overview:1,pull:11,put:11,quot:8,readm:4,refer:1,repli:8,retweet:8,setup:11,sql:5,tabl:1,tag:11,target:0,togeth:11,twclient:[0,1,4],tweet:[8,9,11],twitter:11,twitter_api:0,unreleas:2,user:[9,10,11],vignett:1,word:11,work:5}})