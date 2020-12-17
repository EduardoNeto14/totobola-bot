import pymongo

async def is_admin(ctx):
        database = pymongo.MongoClient(port= 27017)
        properties = database["totobola"]["properties"].find_one({}, {"_id" : 0, "admin" : 1})

        if ctx.author.id in properties["admin"] : return True        

        return False

async def database_exists(ctx):
        database = pymongo.MongoClient(port = 27017)
        
        if "totobola" in database.list_database_names() : return True

        return False

async def is_comp(ctx):
        database = pymongo.MongoClient(port= 27017)
        if ctx.message.content.split()[1] not in database["totobola"].list_collection_names(): return False
        
        return True