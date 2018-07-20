import json
import os
from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
from tweepy import API
from twitter_keys import *

# para dormir al bot en caso de abusos...
from time import sleep  # , strftime

# Formatear timestamp de tweets
import datetime

from modulos.gramatical import generar_archivos_ct_y_dic, MarkovGramatical, DiccionarioGramatical
from modulos.generacion import MarkovGenerador
from modulos.otros import user_input_twitter, crear_dir
from nltk import pos_tag


# Firebase dependencies
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Credenciales firebase
cred = credentials.Certificate("./bot-literario-c7205bcfd010.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# doc_ref = db.collection(u'users').document(u'alovelace')
# doc_ref.set({
#     u'first': u'Name',
#     u'last': u'Last name',
#     u'born': 1993,
#      u'dateExample': fff
# })


nombre = 'rayuela'

print("Se cargara ./textos/" + nombre + ".txt")

dir_generados = os.path.join(".", "generados")
ruta_dic = os.path.join(dir_generados, nombre + ".dic.pickle")
ruta_markov_gramatical = os.path.join(
    dir_generados, nombre + ".markov-gramatical.pickle")
ruta_markov_generador = os.path.join(
    dir_generados, nombre + ".markov-generador.pickle")

dir_user_logs = os.path.join(".", "user_logs")
ruta_log_user = os.path.join(
    dir_user_logs, "twitter." + nombre + ".userlog.txt")


diccionario = DiccionarioGramatical()
diccionario.cargar(ruta_dic)

mgram = MarkovGramatical()
mgram.cargar(ruta_markov_gramatical)

mgen = MarkovGenerador()
mgen.cargar(ruta_markov_generador)


class listener(StreamListener):

    def __init__(self, botname="Julio", mode="dev"):
        """constructor
        
        botname : str, optional
            Nombre del bot (the default is "Julio", which Julio Cortázar)
        mode : str, optional
            Modo de pruebas o producción 
            (Para responder en Twitter) (the default is "dev", which pruebas)
        
        """

        self.botname = botname
        self.mode = mode

    #def on_status(self,status):
    #    print("STATUS",status._json)

    def on_data(self, data):
        data = json.loads(data)
        username = data["user"]["screen_name"]
        user_id = data["user"]["id"]
        tweet_id = data["id"]
        timestamp = datetime.datetime.strptime(
            data["created_at"], '%a %b %d %H:%M:%S +0000 %Y')

        #if "extended_tweet" in dict(data).keys():
        tweet_text = data["text"]

        print(data["user"]["id"])

        #TODO geopunto y país
        # if data["place"] is "None":
        #     country_code = None
        # else:
        #     country_code = data["place"]["country_code"]
        # if data["geo"] is "None":
        #     geo = None
        # else:
        #     geo = data["geo"]

        # crea directorio logs si no existe, faltaba llamar la función.
        crear_dir(dir_user_logs)
        entrada = user_input_twitter(tweet_text, ruta_log=ruta_log_user)
        ultima_palabra = entrada.split(' ')[-1]
        ultima_categoria = pos_tag([ultima_palabra])[0][1]
        siguiente_categoria = mgram.obtener_siguiente_categoria(
            ultima_categoria)
        siguiente_palabra = diccionario.escoger_palabra_de_categoria(
            siguiente_categoria)
        respuesta = mgen.generar_texto(siguiente_palabra)

        try:
            # no responder tweet instantáneamente, se ve muy de stalker
            api = API(auth)
            if self.mode.__eq__("prod"):
                sleep(5)

            # Muestra en terminal conversación
            print(username + "'s tweet:", tweet_id, tweet_text)
            #print(data["geo"])
            # mostrar en consola la respuesta
            print("Respuesta Julio: " + respuesta)
            #print(type(data["place"]),data["geo"])
            # self.botname responde tweet si está en modo producción...
            if self.mode.__eq__("prod"):
                api.update_status("@" + username + " " +
                                  respuesta, in_reply_to_status_id=tweet_id)

            # Salvar conversación en Firestore
            # Referencia a documento de firebase
            doc_ref = db.collection(u'tweets_' + self.mode).document()
            # Diccionario para guardar en Firestore
            to_save = {
                u'bot': self.botname,
                u'user': username,
                u'tweet_id': tweet_id,
                u'answer_bot': respuesta,
                u'tweet_text': tweet_text,
                u'timestamp': timestamp,
                u'user_id': user_id
                #TODO geopunto y país
                # u'country_code': country_code,
                # u'geo': geo
            }
            doc_ref.set(to_save)

        except Exception as exc:
            print("ocurrió la excepción", exc)
        return True

    def on_error(self, status_code):
        # 30 minutos de espera en caso de un error
        secs = 1800
        if status_code == 420:
            # Se ha intentando iniciar sesión muchas veces en poco tiempo.
            print("Err: " + status_code + " - Enhance Your Calm!")
            print("Reconectando en", secs, "secs")
            sleep(secs)
        return True

    def on_timeout(self):
        print("Time Out...")
        sleep(10)
        return True


if __name__ == '__main__':
    #ment = API(auth)
    #mentions = ment.mentions_timeline()
    #mentions = json.loads(mentions)
    #for m in mentions:
    #print(mentions[0].text)
    print("Se iniciara el stream")
    # Para iniciar de nuevo el streaming en caso de algún error
    while True:
        auth = OAuthHandler(ConsumerKey, ConsumerSecret)
        auth.set_access_token(AccessToken, AccessTokenSecret)
        # Seleccionar mode="prod" si está ya es para correrlo en twitter
        # mode="dev" es para pruebas, por lo tanto no escribe en twitter
        # , tweet_mode="extended")
        twitterStream = Stream(auth, listener(mode="listener"))
        #twitterStream.filter(track=["@CEstocastico", "@cestocastico"])
        #twitterStream.filter(track=["@CortazarEstoc", "@cortazarestoc"])
        twitterStream.filter(track=["trump"])
