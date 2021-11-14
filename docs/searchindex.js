Search.setIndex({docnames:["api/modules","api/twclient","changelog","index","license","readme","vignettes/extract","vignettes/fetch"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["api/modules.rst","api/twclient.rst","changelog.rst","index.rst","license.rst","readme.rst","vignettes/extract.rst","vignettes/fetch.rst"],objects:{"":[[1,0,0,"-","twclient"]],"twclient.authpool":[[1,1,1,"","AuthPoolAPI"]],"twclient.cli":[[1,2,1,"","cli"]],"twclient.error":[[1,3,1,"","BadSchemaError"],[1,3,1,"","BadTagError"],[1,3,1,"","BadTargetError"],[1,3,1,"","CapacityError"],[1,3,1,"","NotFoundError"],[1,3,1,"","ProtectedUserError"],[1,3,1,"","ReadFailureError"],[1,3,1,"","SemanticError"],[1,3,1,"","TWClientError"],[1,3,1,"","TwitterAPIError"],[1,3,1,"","TwitterLogicError"],[1,3,1,"","TwitterServiceError"],[1,2,1,"","dispatch_tweepy"]],"twclient.error.BadTagError":[[1,4,1,"","tag"]],"twclient.error.BadTargetError":[[1,4,1,"","targets"]],"twclient.error.CapacityError":[[1,5,1,"","tweepy_is_instance"]],"twclient.error.NotFoundError":[[1,5,1,"","tweepy_is_instance"]],"twclient.error.ProtectedUserError":[[1,5,1,"","tweepy_is_instance"]],"twclient.error.ReadFailureError":[[1,5,1,"","tweepy_is_instance"]],"twclient.error.TWClientError":[[1,4,1,"","exit_status"],[1,4,1,"","message"]],"twclient.error.TwitterAPIError":[[1,4,1,"","api_code"],[1,5,1,"","from_tweepy"],[1,6,1,"","http_code"],[1,4,1,"","response"],[1,5,1,"","tweepy_is_instance"]],"twclient.job":[[1,1,1,"","ApiJob"],[1,1,1,"","ApplyTagJob"],[1,1,1,"","CreateTagJob"],[1,1,1,"","DeleteTagJob"],[1,1,1,"","FollowGraphJob"],[1,1,1,"","FollowersJob"],[1,1,1,"","FriendsJob"],[1,1,1,"","InitializeJob"],[1,1,1,"","Job"],[1,1,1,"","TagJob"],[1,1,1,"","TargetJob"],[1,1,1,"","TweetsJob"],[1,1,1,"","UserInfoJob"]],"twclient.job.ApiJob":[[1,4,1,"","allow_api_errors"],[1,4,1,"","api"],[1,4,1,"","load_batch_size"],[1,5,1,"","validate_targets"]],"twclient.job.ApplyTagJob":[[1,4,1,"","resolve_mode"],[1,5,1,"","run"]],"twclient.job.CreateTagJob":[[1,5,1,"","run"]],"twclient.job.DeleteTagJob":[[1,5,1,"","run"]],"twclient.job.FollowGraphJob":[[1,6,1,"","direction"],[1,4,1,"","resolve_mode"],[1,5,1,"","run"]],"twclient.job.FollowersJob":[[1,4,1,"","direction"]],"twclient.job.FriendsJob":[[1,4,1,"","direction"]],"twclient.job.InitializeJob":[[1,5,1,"","run"]],"twclient.job.Job":[[1,4,1,"","engine"],[1,5,1,"","ensure_schema_version"],[1,5,1,"","get_or_create"],[1,5,1,"","run"],[1,4,1,"","session"]],"twclient.job.TagJob":[[1,4,1,"","tag"]],"twclient.job.TargetJob":[[1,4,1,"","allow_missing_targets"],[1,6,1,"","bad_targets"],[1,6,1,"","good_targets"],[1,6,1,"","missing_targets"],[1,6,1,"","resolve_mode"],[1,5,1,"","resolve_targets"],[1,6,1,"","resolved"],[1,4,1,"","targets"],[1,6,1,"","users"],[1,5,1,"","validate_targets"]],"twclient.job.TweetsJob":[[1,4,1,"","max_tweets"],[1,4,1,"","old_tweets"],[1,4,1,"","resolve_mode"],[1,5,1,"","run"],[1,4,1,"","since_timestamp"]],"twclient.job.UserInfoJob":[[1,4,1,"","resolve_mode"],[1,5,1,"","run"]],"twclient.models":[[1,1,1,"","Follow"],[1,1,1,"","FromTweepyInterface"],[1,1,1,"","Hashtag"],[1,1,1,"","HashtagMention"],[1,1,1,"","List"],[1,1,1,"","ListFromTweepyInterface"],[1,1,1,"","Media"],[1,1,1,"","MediaMention"],[1,1,1,"","MediaType"],[1,1,1,"","MediaVariant"],[1,1,1,"","SchemaVersion"],[1,1,1,"","StgFollow"],[1,1,1,"","Symbol"],[1,1,1,"","SymbolMention"],[1,1,1,"","Tag"],[1,1,1,"","TimestampsMixin"],[1,1,1,"","Tweet"],[1,1,1,"","UniqueMixin"],[1,1,1,"","Url"],[1,1,1,"","UrlMention"],[1,1,1,"","User"],[1,1,1,"","UserData"],[1,1,1,"","UserList"],[1,1,1,"","UserMention"],[1,1,1,"","UserTag"]],"twclient.models.Follow":[[1,4,1,"","follow_id"],[1,4,1,"","source_user_id"],[1,4,1,"","target_user_id"],[1,4,1,"","valid_end_dt"],[1,4,1,"","valid_start_dt"]],"twclient.models.FromTweepyInterface":[[1,5,1,"","from_tweepy"]],"twclient.models.Hashtag":[[1,4,1,"","hashtag_id"],[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","name"],[1,4,1,"","unique_hash"]],"twclient.models.HashtagMention":[[1,4,1,"","end_index"],[1,4,1,"","hashtag_id"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","modified_dt"],[1,4,1,"","start_index"],[1,4,1,"","tweet_id"]],"twclient.models.List":[[1,4,1,"","api_response"],[1,4,1,"","create_dt"],[1,4,1,"","description"],[1,4,1,"","display_name"],[1,5,1,"","from_tweepy"],[1,4,1,"","full_name"],[1,4,1,"","insert_dt"],[1,4,1,"","list_id"],[1,4,1,"","member_count"],[1,4,1,"","mode"],[1,4,1,"","modified_dt"],[1,4,1,"","slug"],[1,4,1,"","subscriber_count"],[1,4,1,"","uri"],[1,4,1,"","user_id"]],"twclient.models.ListFromTweepyInterface":[[1,5,1,"","list_from_tweepy"]],"twclient.models.Media":[[1,4,1,"","aspect_ratio_height"],[1,4,1,"","aspect_ratio_width"],[1,4,1,"","duration"],[1,5,1,"","from_tweepy"],[1,4,1,"","insert_dt"],[1,4,1,"","media_id"],[1,4,1,"","media_type_id"],[1,4,1,"","media_url_id"],[1,4,1,"","modified_dt"]],"twclient.models.MediaMention":[[1,4,1,"","end_index"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","media_id"],[1,4,1,"","modified_dt"],[1,4,1,"","start_index"],[1,4,1,"","tweet_id"],[1,4,1,"","twitter_display_url"],[1,4,1,"","twitter_expanded_url"],[1,4,1,"","twitter_short_url"]],"twclient.models.MediaType":[[1,5,1,"","from_tweepy"],[1,4,1,"","insert_dt"],[1,4,1,"","media_type_id"],[1,4,1,"","modified_dt"],[1,4,1,"","name"],[1,4,1,"","unique_hash"]],"twclient.models.MediaVariant":[[1,4,1,"","bitrate"],[1,4,1,"","content_type"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","media_id"],[1,4,1,"","modified_dt"],[1,4,1,"","url_id"]],"twclient.models.SchemaVersion":[[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","version"]],"twclient.models.Symbol":[[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","name"],[1,4,1,"","symbol_id"],[1,4,1,"","unique_hash"]],"twclient.models.SymbolMention":[[1,4,1,"","end_index"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","modified_dt"],[1,4,1,"","start_index"],[1,4,1,"","symbol_id"],[1,4,1,"","tweet_id"]],"twclient.models.Tag":[[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","name"],[1,4,1,"","tag_id"]],"twclient.models.Tweet":[[1,4,1,"","api_response"],[1,4,1,"","content"],[1,4,1,"","create_dt"],[1,4,1,"","favorite_count"],[1,5,1,"","from_tweepy"],[1,4,1,"","in_reply_to_status_id"],[1,4,1,"","in_reply_to_user_id"],[1,4,1,"","insert_dt"],[1,4,1,"","lang"],[1,4,1,"","modified_dt"],[1,4,1,"","quoted_status_id"],[1,4,1,"","retweet_count"],[1,4,1,"","retweeted_status_id"],[1,4,1,"","source"],[1,4,1,"","truncated"],[1,4,1,"","tweet_id"],[1,4,1,"","user_id"]],"twclient.models.UniqueMixin":[[1,5,1,"","as_unique"]],"twclient.models.Url":[[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","unique_hash"],[1,4,1,"","url"],[1,4,1,"","url_id"]],"twclient.models.UrlMention":[[1,4,1,"","description"],[1,4,1,"","end_index"],[1,4,1,"","expanded_short_url"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","modified_dt"],[1,4,1,"","start_index"],[1,4,1,"","status"],[1,4,1,"","title"],[1,4,1,"","tweet_id"],[1,4,1,"","twitter_display_url"],[1,4,1,"","twitter_short_url"],[1,4,1,"","url_id"]],"twclient.models.User":[[1,5,1,"","from_tweepy"],[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","user_id"]],"twclient.models.UserData":[[1,4,1,"","api_response"],[1,4,1,"","create_dt"],[1,4,1,"","description"],[1,4,1,"","display_name"],[1,4,1,"","followers_count"],[1,4,1,"","friends_count"],[1,5,1,"","from_tweepy"],[1,4,1,"","insert_dt"],[1,4,1,"","listed_count"],[1,4,1,"","location"],[1,4,1,"","modified_dt"],[1,4,1,"","protected"],[1,4,1,"","screen_name"],[1,4,1,"","url_id"],[1,4,1,"","user_data_id"],[1,4,1,"","user_id"],[1,4,1,"","verified"]],"twclient.models.UserList":[[1,4,1,"","list_id"],[1,4,1,"","user_id"],[1,4,1,"","user_list_id"],[1,4,1,"","valid_end_dt"],[1,4,1,"","valid_start_dt"]],"twclient.models.UserMention":[[1,4,1,"","end_index"],[1,4,1,"","insert_dt"],[1,5,1,"","list_from_tweepy"],[1,4,1,"","mentioned_user_id"],[1,4,1,"","modified_dt"],[1,4,1,"","start_index"],[1,4,1,"","tweet_id"]],"twclient.models.UserTag":[[1,4,1,"","insert_dt"],[1,4,1,"","modified_dt"],[1,4,1,"","tag_id"],[1,4,1,"","user_id"],[1,4,1,"","user_tag_id"]],"twclient.target":[[1,1,1,"","ScreenNameTarget"],[1,1,1,"","SelectTagTarget"],[1,1,1,"","Target"],[1,1,1,"","TwitterListTarget"],[1,1,1,"","UserIdTarget"]],"twclient.target.ScreenNameTarget":[[1,4,1,"","allowed_resolve_modes"],[1,5,1,"","resolve"]],"twclient.target.SelectTagTarget":[[1,4,1,"","allowed_resolve_modes"],[1,5,1,"","resolve"]],"twclient.target.Target":[[1,6,1,"","allowed_resolve_modes"],[1,6,1,"","bad_targets"],[1,6,1,"","context"],[1,6,1,"","good_targets"],[1,6,1,"","missing_targets"],[1,4,1,"","randomize"],[1,5,1,"","resolve"],[1,6,1,"","resolved"],[1,4,1,"","targets"],[1,6,1,"","users"]],"twclient.target.TwitterListTarget":[[1,4,1,"","allowed_resolve_modes"],[1,5,1,"","resolve"]],"twclient.target.UserIdTarget":[[1,4,1,"","allowed_resolve_modes"],[1,5,1,"","resolve"]],"twclient.twitter_api":[[1,1,1,"","TwitterApi"]],"twclient.twitter_api.TwitterApi":[[1,4,1,"","auths"],[1,5,1,"","followers_ids"],[1,5,1,"","friends_ids"],[1,5,1,"","get_list"],[1,5,1,"","list_members"],[1,5,1,"","lookup_users"],[1,5,1,"","make_api_call"],[1,4,1,"","pool"],[1,5,1,"","user_timeline"]],twclient:[[1,0,0,"-","authpool"],[1,0,0,"-","cli"],[1,0,0,"-","error"],[1,0,0,"-","job"],[1,0,0,"-","models"],[1,0,0,"-","target"],[1,0,0,"-","twitter_api"]]},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","function","Python function"],"3":["py","exception","Python exception"],"4":["py","attribute","Python attribute"],"5":["py","method","Python method"],"6":["py","property","Python property"]},objtypes:{"0":"py:module","1":"py:class","2":"py:function","3":"py:exception","4":"py:attribute","5":"py:method","6":"py:property"},terms:{"140":1,"16":1,"2":[1,2],"2019":4,"2021":4,"3200":1,"5000":1,"9":1,"abstract":1,"boolean":1,"case":1,"catch":1,"class":[1,2],"default":1,"do":[1,4],"final":1,"float":1,"function":1,"int":1,"long":1,"new":1,"null":1,"public":1,"return":1,"short":1,"static":1,"switch":1,"true":1,"while":1,A:[1,2,4],AND:4,AS:4,As:1,At:1,BE:4,BUT:4,But:1,FOR:4,For:1,IN:4,IS:4,If:1,In:1,Is:1,It:1,NO:4,NOT:4,No:1,Not:1,OF:4,OR:4,Such:1,THE:4,TO:4,That:1,The:[1,2,5],There:1,These:1,WITH:4,__init__:1,abc:1,abl:1,abort:1,about:[1,5],abov:4,accept:1,access:[1,2],accord:1,account:1,across:1,action:4,actual:1,ad:[1,5],add:[1,5],addit:1,address:1,after:[1,5],again:1,against:1,all:[1,2,4,5],allow:1,allow_api_error:1,allow_missing_target:1,allow_missing_us:1,allowed_resolve_mod:1,alreadi:1,also:[1,5],alwai:1,amount:1,an:[1,4,5],analogu:1,analysi:[1,2,5],analyt:1,android:1,ani:[1,4,5],anoth:1,anyth:1,api:[2,3,5],api_cod:1,api_respons:1,apijob:1,app:[1,2],appear:1,appli:[1,5],applic:1,applytagjob:1,appropri:1,approxim:1,ar:[1,2,5],arbitrari:[1,2],arbitrarili:5,argument:1,aris:4,around:1,as_uniqu:1,aspect:1,aspect_ratio_height:1,aspect_ratio_width:1,assign:1,associ:[1,4],attempt:1,attribut:1,attributeerror:1,auth:1,authent:2,authhandl:1,author:4,authpool:0,authpoolapi:1,autoincr:1,autom:2,avail:1,avoid:[1,5],b:1,back:1,backend:2,bad:1,bad_target:1,badschemaerror:1,badtagerror:1,badtargeterror:1,base:[1,2],basic:5,batch:1,becaus:1,been:[1,5],befor:1,behavior:1,being:1,bio:1,bit:1,bitrat:1,bodi:1,bool:1,both:[1,2],calcul:1,call:1,can:[1,2,5],candid:1,cannot:1,capabl:1,capac:1,capacity_retri:1,capacity_sleep:1,capacityerror:1,cashtag:1,caught:1,caus:1,ceas:1,certain:1,chain:1,chang:[1,2],changelog:3,charact:1,charg:4,check:[1,2],cl:1,claim:4,classmethod:1,cli:0,click:1,client:[1,5],co:1,code:1,collect:2,column:1,com:1,combin:1,command:[1,2,5],common:1,commun:1,compat:1,condit:[1,4],config:5,configur:[1,5],congress:1,congression:1,connect:[1,4],consequ:1,consid:1,consist:1,constraint:1,construct:1,consum:[1,5],contain:1,content:1,content_typ:1,context:1,continu:1,contract:4,control:1,conveni:2,convert:1,copi:4,copyright:4,correct:[1,2],correctli:1,correspond:1,corrupt:1,cost:1,could:1,count:1,creat:[1,5],create_dt:1,createtagjob:1,creation:1,credenti:[1,5],crude:1,cspan:1,current:1,cursor:1,damag:4,data:[1,2,3,5],databas:[1,2,5],date:1,db:[1,5],deal:4,decl_api:1,declar:1,dedic:1,dedup:1,dedupl:1,defaut:1,defer:1,defin:1,deleg:1,delet:1,deletetagjob:1,depend:1,descend:1,descript:1,desktop:1,destin:1,detail:[1,2,5],detect:1,determin:1,differ:1,direct:1,directori:[6,7],discard:1,discuss:1,dispatch:1,dispatch_tweepi:1,displai:1,display_nam:1,disposit:1,distribut:4,document:[2,4],doe:1,doesn:1,domain:1,done:1,drop:[1,5],duplic:1,durat:1,dure:1,e:1,each:1,eas:5,easi:2,easier:1,edg:[1,2],effect:1,effici:1,either:1,els:1,empti:1,encapsul:1,encount:1,end:1,end_index:1,endpoint:1,engin:1,enough:1,ensur:[1,2],ensure_schema_vers:1,enter:1,entir:1,entiti:[1,2],entrypoint:1,error:0,etc:1,evalu:1,even:1,event:4,eventu:1,ex:1,exactli:1,exampl:[1,5,6],exc:1,except:1,execut:1,exist:[1,5],exit:1,exit_statu:1,expanded_short_url:1,expect:1,expos:1,express:[1,4],extend:1,extens:[1,2],extract:[1,2,3],fact:1,fail:1,fals:1,favorit:1,favorite_count:1,featur:5,fetch:[1,2,3,5],field:1,file:[1,4,5],first:[1,2],fit:4,focu:5,focus:1,follow:[1,2,4,5],follow_id:1,followers_count:1,followers_id:1,followersjob:1,followgraphjob:1,foreign:1,form:1,format:[1,2],found:1,free:[1,4],friend:[1,5],friends_count:1,friends_id:1,friendsjob:1,from:[1,4],from_tweepi:1,fromtweepyinterfac:1,fulfil:1,full:1,full_nam:1,furnish:4,further:[1,2],futur:1,g:[1,5],gave:1,gener:1,get:[1,5],get_list:1,get_or_cr:1,give:1,given:1,goal:5,goe:1,good:1,good_target:1,grant:4,graph:[1,2],greater:[1,2],group:2,ha:1,handl:[1,5],hash:1,hashtag:[1,2],hashtag_id:1,hashtagment:1,have:[1,5],help:[1,5],here:[1,2],herebi:4,high:[1,5],higher:[1,5],histor:1,hit:1,holder:4,hook:1,housekeep:1,how:1,http:1,http_code:1,hundr:1,hydrat:1,i:1,id:1,identifi:1,ignor:1,implement:1,impli:4,in_reply_to_status_id:1,in_reply_to_user_id:1,includ:[1,4],incompat:1,independ:2,index:[1,3],indic:1,info:[2,5],inform:1,ingest:[1,2],initi:[1,5],initializejob:1,input:1,insert:1,insert_dt:1,instanc:1,instanti:1,instead:1,institut:4,integ:1,integr:[6,7],intend:1,interfac:[1,2],interpret:1,interrupt:1,involv:1,iphon:1,issu:5,item:1,its:1,itself:1,job:0,jointli:1,journalist:1,json:1,just:1,keep:2,kei:[1,5],keyword:1,kind:[1,4],know:1,kwarg:1,l:5,lang:1,languag:1,larg:1,larger:1,last:1,later:[1,5],latter:1,lead:1,least:1,leav:1,led:1,left:1,length:1,level:[1,5],liabil:4,liabl:4,licens:3,lifetim:1,like:[1,2],limit:[1,4,5],line:[1,2,5],link:1,list:[1,2,5],list_from_tweepi:1,list_id:1,list_memb:1,listed_count:1,listfromtweepyinterfac:1,load:[1,2,5],load_batch_s:1,locat:1,log:1,logic:1,longer:1,look:1,lookup:1,lookup_us:1,low:1,lower:1,ly:1,made:1,mai:1,main:1,make:[1,2],make_api_cal:1,mani:[1,2,5],massachusett:4,max_item:1,max_tweet:1,mean:1,media:1,media_id:1,media_type_id:1,media_url_id:1,mediament:1,mediatyp:1,mediavari:1,member:1,member_count:1,membership:[1,2],memori:1,mention:[1,2],mentioned_user_id:1,merchant:4,merg:[1,4],messag:1,meta:1,method:1,might:1,migrat:1,mime:1,minim:1,miss:1,missing_target:1,mit:5,mixin:1,mode:1,model:[0,2],modif:1,modifi:[1,4],modified_dt:1,more:[1,2],most:1,multipl:[1,5],multiplex:1,must:1,mutabl:1,n:5,name:1,need:[1,5],network:1,newer:1,newest:1,newli:1,next:1,non:1,none:1,nonexist:1,noninfring:4,normal:[1,2,5],notabl:2,note:1,notfounderror:1,noth:1,notic:4,notimplementederror:1,notion:1,now:1,number:1,numer:1,obj:1,object:[1,2],observ:1,obtain:4,occur:1,offer:5,old_tweet:1,older:1,onc:1,one:1,onli:[1,2,5],oper:1,opposit:1,option:1,order:1,origin:1,orm:1,other:[1,4],otherwis:[1,4],out:[1,4,5],over:[1,2],overrid:1,own:1,owner_id:1,owner_screen_nam:1,packag:[1,5],page:1,paramet:1,pars:1,particular:[1,4],partwai:1,pass:1,pend:1,per:1,period:1,permiss:4,permit:4,persist:[1,5],person:4,photo:1,place:1,platform:1,pool:1,popul:1,portion:4,posit:1,possibl:1,post:1,postgr:5,postgresql:5,posting_us:1,practic:1,prefix:1,prepend:1,present:1,preserv:1,previou:1,previous:1,primari:1,primit:5,privat:1,probabl:1,problem:1,process:[1,2,5],profil:[1,5],program:1,project:2,properti:1,protect:1,protectedusererror:1,provid:[1,4,5],proxi:1,publish:4,pull:5,purpos:4,queri:[1,5],quit:1,quot:1,quoted_status_id:1,rais:1,random:1,rate:[1,5],rather:1,ratio:1,raw:[1,5],re:1,read:1,readfailureerror:1,readm:3,real:1,reason:1,receiv:1,recent:1,record:1,reduc:1,refer:1,reflect:1,regular:1,rel:1,relat:2,relationship:1,reli:1,remain:1,render:1,repeatedli:5,replac:1,repli:[1,2],repres:1,request:1,requir:1,research:5,resolv:1,resolve_mod:1,resolve_target:1,resourc:1,respect:1,respons:[1,5],restrict:4,result:1,retain:1,retri:1,retriev:1,retweet:[1,2],retweet_count:1,retweeted_status_id:1,revers:1,right:4,rise:1,roll:1,row:1,rt:1,run:1,s:1,safe:1,same:1,sane:1,saniti:2,save:5,scd:[1,2],schema:[1,5],schemavers:1,screen:1,screen_nam:1,screennametarget:1,script:1,seamlessli:5,searchabl:1,second:1,secret:5,see:1,select:1,selecttagtarget:1,self:1,sell:4,semant:2,semanticerror:1,send:1,sensibl:1,separ:1,sequenti:1,servic:1,session:1,set:[1,5],setup:5,sever:1,shall:4,shorten:1,should:1,show:1,shown:5,sign:1,signific:1,similarli:5,simplifi:1,simultan:1,since_id:1,since_timestamp:1,size:1,skip:1,slash:1,sleep:1,slow:1,slower:1,slug:1,smartphon:1,so:[1,4],socialmachin:5,softwar:4,some:[1,5],someth:1,sometim:1,somewher:1,sourc:1,source_us:1,source_user_id:1,space:1,special:1,specif:1,specifi:1,speed:1,sql:7,sqlalchemi:[1,2],stabl:[1,2],stage:1,start:1,start_index:1,state:1,statist:1,statu:1,status:1,stgfollow:1,still:1,stock:1,stop:1,store:[1,5],str:1,string:1,stub:1,subclass:1,subject:[4,5],sublicens:4,subscrib:1,subscriber_count:1,subsequ:1,substanti:4,successfulli:1,support:[1,2],suppos:1,sure:1,surplu:1,survey_respondents_2020:1,suspend:1,sy:1,symbol:1,symbol_id:1,symbolment:1,t:1,tabl:1,tag:[1,2,5],tag_id:1,tagjob:1,take:1,target:0,target_us:1,target_user_id:1,targetjob:1,technolog:4,tell:1,temporarili:1,term:1,text:1,than:[1,5],thank:1,thei:1,them:[1,5],themselv:1,thi:[1,2,4,5],thing:1,those:1,though:1,three:1,through:1,thumbnail:1,ticker:1,time:[1,2,5],timelin:1,timestamp:1,timestampsmixin:1,titl:1,todo:[6,7],togeth:1,token:5,tool:5,top:1,tort:4,track:[1,2],transact:1,transpar:1,treat:1,treatment:1,trigger:1,truncat:1,turn:1,twclient:0,twclienterror:1,tweeperror:1,tweepi:[1,5],tweepy_is_inst:1,tweet:[1,2,5],tweet_id:1,tweetsjob:1,twitter1:5,twitter2:5,twitter:[1,2,5],twitter_api:0,twitter_display_url:1,twitter_expanded_url:1,twitter_short_url:1,twitterapi:1,twitterapierror:1,twitterlisttarget:1,twitterlogicerror:1,twitterserviceerror:1,two:[1,5],twurl:5,type:[1,2,5],u:5,ultim:1,unavail:1,underli:1,union:1,uniqu:1,unique_hash:1,uniquemixin:1,unix:1,unless:1,unlik:1,unsupport:1,up:[1,5],updat:1,uri:1,url:[1,5],url_id:1,urlment:1,us:[1,4,5],usabl:1,usag:[1,5],user:[1,2,5],user_data:1,user_data_id:1,user_id:1,user_list_id:1,user_tag:1,user_tag_id:1,user_timelin:1,userdata:1,useridtarget:1,userinfojob:1,userlist:1,userment:1,usertag:1,usual:[1,5],valid:1,valid_end_dt:1,valid_start_dt:1,validate_target:1,valu:1,varieti:2,variou:1,veri:1,verifi:1,version:[1,2],via:[1,2],video:1,view:1,viewer:1,visibl:1,wa:1,wai:1,want:[1,5],warn:1,warranti:4,we:1,web:1,websit:1,well:1,went:1,were:1,what:1,whatev:1,when:1,where:1,whether:[1,4],which:1,who:[1,5],whom:4,whose:1,within:1,without:[1,4,5],work:1,worri:5,would:1,wrap:1,wrapper:1,wrong:1,wwbrannon:5,xxxxx:5,xxxxxx:5,y:5,yield:1,you:5},titles:["API Documentation","API Documentation","Changelog","Twclient Documentation","License","README","Extracting data","Fetching data"],titleterms:{The:4,ad:2,api:[0,1],authpool:1,changelog:2,cli:1,data:[6,7],document:[0,1,3],error:1,extract:6,fetch:7,indic:3,job:1,licens:4,mit:4,model:1,overview:3,readm:5,refer:3,tabl:3,target:1,twclient:[1,3,5],twitter_api:1,unreleas:2,vignett:3}})