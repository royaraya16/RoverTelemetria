kml='<Placemark><LineString><coordinates>'

#esto iría dentro de un loop para que los meta todos en una nueva linea
kml+='\n'+str(longitud)+','+str(latitud)
#hasta aqui

kml+='\n </coordinates></LineString></Placemark>'
with open('prueba1.kml', 'w+') as data_file:
    data_file.write(kml)
    data_file.flush()
