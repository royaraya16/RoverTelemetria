import os
import wx
import random
import serial
import time

from wxmplot.plotframe import PlotFrame

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas
import numpy as np
import pylab

#Clase que me va a recoger los datos de los diferentes sensores
#Por ahora lo q se quiere obtener es:
    #=> Direccion de magnetometro
    #=> Velocidad angular de Gyro
    #=> Corriente M1 & M2
    #=> Porcentaje de PWM de M1 & M2
    #=> Velocidad de Encoders M1 & M2
    #=> Latitud Longitud GPS

COMPASS, PWM1, PWM2, \
V1, V2, LATITUD, LONGITUD, ALTITUD, COMPASSGOAL, \
TARGET, POSX, POSY, ESTADO, MOVIENDOSE, FIX = range(15)


class DataGen(object):
    """ Generando datos random para plotear
    """
    def __init__(self, init=50):
        self.data = self.init = init

    def next(self):
        self._recalc_data()
        x = int(random.random() * 100)
        if x > 50:
            return self.data
        else:
            return self.datos2()

    def _recalc_data(self):
        delta = random.uniform(-0.5, 0.5)
        r = random.random()

        if r > 0.9:
            self.data += delta * 15
        elif r > 0.8:
            # attraction to the initial value
            delta += (0.5 if self.init > self.data else -0.5)
            self.data += delta
        else:
            self.data += delta

    def datos2(self):
        return int(random.random() * 100)


class DataAQ(object):

    def __init__(self):

        #Se define el arreglo de datos

        self.DAQarray = []

        self.DATAGEN = DataGen()

        #Definiendo el puerto Serie de donde se van a leer los datos

        #self.xBee = serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=1.0)
        #self.xBee.close()

        #Definiendo el string que va a ir actualizando con la lista de datos

        self.dataString = ""

    def get(self):
        self.DAQarray = []

        #self.xBee.open()
        #line = self.xBee.readline()
        #self.xBee.close()

        #self.DAQarray = np.fromstring(line.decode('ascii', errors='replace'),
            #sep=' ')

        #self.DAQarray = line.split()

        #considerar cambiar esto por el metodo q se usa para agarrar los datos
        #del .txt del GPS

        for i in range(15):
            self.DAQarray.append(self.DATAGEN.next())

        #print self.DAQarray.split()

        return self.DAQarray


#Clase que simboliza la ventana q se va a abrir, dentro de esta ventana
#se pone todo lo demas


class ArlissMonitoringFrame(wx.Frame):

    title = 'Sensors Monitoring'

    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title, size=(700, 700))

        os.system("banner ARLISS")

        #Partiendo la ventana en 2 paneles, en uno de ellos van los graficos
        ##en otro los botones y demas

        self.Maximize()
        #Funcion para abrir la ventana maximizada

        self.sp = wx.SplitterWindow(self)
        self.p1 = wx.Panel(self.sp, style=wx.SUNKEN_BORDER)
        self.p2 = wx.Panel(self.sp, style=wx.SUNKEN_BORDER)
        self.sp.SplitVertically(self.p1, self.p2, 250)

        self.keycode = ''
        self.Pause = False

        self.plotframe = None

        #Se crean los arreglos que van a guardar los datos

        self.dataAQ = DataAQ()

        #Clase que genera datos random, para pruebas

        self.datagen = DataGen()

        #Arreglo con los datos

        self.datos = [[], [], [], [], [],
         [], [], [], [], [], [], [], [], [], []]

        self.datosGPS = [[], []]

        for line in open('GPS.txt', 'r'):
            self.datosGPS[0].append(line.split()[0])
            self.datosGPS[1].append(line.split()[1])

        #Se corren funciones para inicializar y crear paneles y el menu
        #En el panel es donde esta todo

        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()

        #se inicializan los timers
        #Super importantes, cada 100ms ocurre un evento y se corre una funcion
        #en este caso: self.on_redraw_timer, la cual redibuja los graficos

        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(100)

        #Texto estatico

        wx.StaticText(self.p1, -1, "Latitud \t\t\t Longitud", (20, 80))
        wx.StaticText(self.p1, -1, "Altura: ", (20, 605))
        wx.StaticText(self.p1, -1, "Distancia: ", (20, 620))
        wx.StaticText(self.p1, -1, "Estado: ", (20, 635))
        wx.StaticText(self.p1, -1, "Moving ", (20, 650))
        wx.StaticText(self.p1, -1, "Fix: ", (20, 665))

        self.textoAltura = wx.StaticText(self.p1, -1, "0", (100, 605))
        self.textoDistancia = wx.StaticText(self.p1, -1, "0", (100, 620))
        self.textoEstado = wx.StaticText(self.p1, -1, "0", (100, 635))
        self.textoMoviendose = wx.StaticText(self.p1, -1, "0", (100, 650))
        self.textoFix = wx.StaticText(self.p1, -1, "0", (100, 665))

        #Se crea una ventana para imprimir los datos de latitud y longitud

        self.logger = wx.TextCtrl(self.p1, 5, "", wx.Point(0, 100),
             wx.Size(250, 500), wx.TE_MULTILINE | wx.TE_READONLY)

        #Boton de prueba, cuando se clickea se crea un evento
        #y se corre una funcion

        self.pauseButton = wx.Button(
            self.p1, wx.ID_STOP, pos=(10, 25))
        self.pauseButton.Bind(wx.EVT_BUTTON, self.onPause)

        self.saveButton = wx.Button(
            self.p1, wx.ID_SAVE, pos=(150, 25))
        self.saveButton.Bind(wx.EVT_BUTTON, self.Save)

    #Funcion que se corre cada vez que se presiona el boton

    def Save(self, event):
        self.saveData(self)

    def onPause(self, event):

        if not self.Pause:
            self.Pause = True
        else:
            self.Pause = False

    def ShowPlotFrame(self, do_raise=True, clear=True):
        "make sure plot frame is enabled, and visible"
        if self.plotframe is None:
            self.plotframe = PlotFrame(self)
            self.has_plot = False
        try:
            self.plotframe.Show()
        except wx.PyDeadObjectError:
            self.plotframe = PlotFrame(self)
            self.plotframe.Show()

        if do_raise:
            self.plotframe.Raise()
        if clear:
            self.plotframe.panel.clear()
            self.plotframe.reset_config()

    #Creando el menu con todos las diferentes pesta;as y accesos

    def create_menu(self):
        self.menubar = wx.MenuBar()

        menu_file = wx.Menu()
        m_expt = menu_file.Append(
            -1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        self.menubar.Append(menu_file, "&File")

        saveMenu = wx.Menu()

        m_Compass = saveMenu.Append(-1, "Plot Compass",
             "Plotear y guardar los datos de la brujula")
        self.Bind(wx.EVT_MENU, self.wxmPlotBrujula, m_Compass)

        m_CompassGoal = saveMenu.Append(-1, "Plot CompassGoal",
             "Plotear y guardar los datos del angulo con respecto a la meta")
        self.Bind(wx.EVT_MENU, self.wxmPlotBrujulaGoal, m_CompassGoal)

        m_PWM1 = saveMenu.Append(-1, "Plot PWM 1",
             "Plotear y guardar los datos del PWM del Motor 1")
        self.Bind(wx.EVT_MENU, self.wxmPlotPWM1, m_PWM1)

        m_PWM2 = saveMenu.Append(-1, "Plot PWM 2",
             "Plotear y guardar los datos del PWM del Motor 2")
        self.Bind(wx.EVT_MENU, self.wxmPlotPWM2, m_PWM2)

        m_V1 = saveMenu.Append(-1, "Plot V1",
             "Plotear y guardar los datos de la velocidad del Motor 1")
        self.Bind(wx.EVT_MENU, self.wxmPlotV1, m_V1)

        m_V2 = saveMenu.Append(-1, "Plot V2",
             "Plotear y guardar los datos de la velocidad del Motor 2")
        self.Bind(wx.EVT_MENU, self.wxmPlotV2, m_V2)

        m_GPS = saveMenu.Append(-1, "Google Earth GPS",
             "Mostrar en Google Earth los datos del GPS")
        self.Bind(wx.EVT_MENU, self.googleEarth, m_GPS)

        m_Altitud = saveMenu.Append(-1, "Plot Altitud",
             "Plotear y guardar los datos de la Altitud")
        self.Bind(wx.EVT_MENU, self.wxmPlotAltitud, m_Altitud)

        m_Target = saveMenu.Append(-1, "Plot Target",
             "Plotear y guardar los datos de la distancia de la meta")
        self.Bind(wx.EVT_MENU, self.wxmPlotTarget, m_Target)

        #Dejemos en standby lo de posX y posY

        m_Estado = saveMenu.Append(-1, "Plot Estado",
             "Plotear y guardar los datos del Estado del Rover")
        self.Bind(wx.EVT_MENU, self.wxmPlotEstado, m_Estado)

        m_Moviendose = saveMenu.Append(-1, "Plot Moviendose",
             "Plotear y guardar los datos del Estado del Movimiento del Rover")
        self.Bind(wx.EVT_MENU, self.wxmPlotMoviendose, m_Moviendose)

        m_Fix = saveMenu.Append(-1, "Plot GPS Fix",
             "Plotear y guardar los datos del Fix del GPS")
        self.Bind(wx.EVT_MENU, self.wxmPlotFix, m_Fix)

        self.menubar.Append(saveMenu, "Plotear Datos")
        self.SetMenuBar(self.menubar)

    #Se crea un panel, el q va a contener los graficos, se inicializan los
    #graficos y se imprimen en el panel self.p2 como una figura.

    def create_main_panel(self):

        self.init_plot()
        self.canvas = FigCanvas(self.p2, -1, self.fig)

    #Se crea la barra de estado que esta en la parte de abajo de la ventana

    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

        #Texto que va en la barra de estado, se puede
        #cambiar por medio de eventos

        self.statusbar.SetStatusText("Sensors Monitoring")

    #Inicializando los graficos, aqui se utiliza mayormente
    #la libreria matplotlib
    #Se indican las propiedades de los graficos y otras cosas

    def init_plot(self):

        #Resolucion del grafico

        self.dpi = 100

        #Se crea el objeto que va a tener el o los graficos,
        #se le indica la resolucion
        #y el tamano

        self.fig = Figure((11, 7.0), dpi=self.dpi)

        #Se le agrega un subplot a la figura llamada PWM,
        #Esta figura va a tener los datos de los 2 PWM
        #se indica que la figura
        #va a tener un arreglo de graficos 2x2 (fila x columna) y que subplot
        #PWM va a ser el primero de los dos subplots.

        self.PWM = self.fig.add_subplot(221)
        self.PWM2 = self.fig.add_subplot(221)

        self.PWM.set_axis_bgcolor('black')
        self.PWM.set_title('PWM', size=12)

        pylab.setp(self.PWM.get_xticklabels(), fontsize=8)
        pylab.setp(self.PWM.get_yticklabels(), fontsize=8)

        #Se plotean datos, pero por primera vez,
        #luego se actualizan con el timer

        self.plot_PWM = self.PWM.plot(
            self.datos[PWM1], linewidth=1, color=(1, 1, 0),)[0]

        self.plot_PWM2 = self.PWM2.plot(
            (self.datos[PWM2]), linewidth=1, color=(1, 0, 0),)[0]
            #Falta PWM2

        self.PWM.legend([self.plot_PWM, self.plot_PWM2], ["PWM1", "PWM2"])

        #Agregando plot de Brujula
        #Aqui van a ir ploteados los datos del angulo con respecto al norte
        #Y el angulo con respecto al goal

        self.Brujula = self.fig.add_subplot(222)
        self.BrujulaGoal = self.fig.add_subplot(222)
        self.Brujula.set_axis_bgcolor('black')
        self.Brujula.set_title('Angulos', size=12)

        pylab.setp(self.Brujula.get_xticklabels(), fontsize=8)
        pylab.setp(self.Brujula.get_yticklabels(), fontsize=8)

        self.plot_Brujula = self.Brujula.plot(
            self.datos[COMPASS], linewidth=1, color=(0, 0, 1),)[0]

        self.plot_BrujulaGoal = self.BrujulaGoal.plot(
            self.datos[COMPASSGOAL], linewidth=1, color=(1, 0, 1),)[0]

        self.Brujula.legend([self.plot_Brujula, self.plot_BrujulaGoal], ["Norte", "Meta"])

        #Agregando plot de Velocidades

        self.Vel = self.fig.add_subplot(223)
        self.Vel2 = self.fig.add_subplot(223)
        self.Vel.set_axis_bgcolor('black')
        self.Vel.set_title('Velocidades', size=12)

        pylab.setp(self.Vel.get_xticklabels(), fontsize=8)
        pylab.setp(self.Vel.get_yticklabels(), fontsize=8)

        self.plot_Vel = self.Vel.plot(
            self.datos[V1], linewidth=1, color=(0, 1, 0),)[0]

        self.plot_Vel2 = self.Vel2.plot(
            self.datos[V2], linewidth=1, color=(1, 1, 0),)[0]

        self.Vel.legend([self.plot_Vel, self.plot_Vel2], ["M1", "M2"])

        #Agregando plot de POS

        self.POS = self.fig.add_subplot(224)
        self.POS.set_axis_bgcolor('black')
        self.POS.set_title('Posiciones', size=12)

        pylab.setp(self.POS.get_xticklabels(), fontsize=8)
        pylab.setp(self.POS.get_yticklabels(), fontsize=8)

        self.plot_POS = self.POS.plot(
            self.datos[POSX], self.datos[POSY], linewidth=1, color=(0, 0, 1),)[0]

    def draw_plot(self):

        xmax_PWM = len(self.datos[PWM1]) if len(self.datos[PWM1]) > 50 else 50
        xmin_PWM = xmax_PWM - 50

        ymin_PWM = round(min(min(self.datos[PWM1]),
         min(self.datos[PWM2])), 0) - 1
        ymax_PWM = round(max(max(self.datos[PWM1]),
         max(self.datos[PWM2])), 0) + 1
        #SACAR EL MINIMO Y MAX DE 2 ARRAYS, PWM1 Y PWM2

        self.PWM.set_xbound(lower=xmin_PWM, upper=xmax_PWM)
        self.PWM.set_ybound(lower=ymin_PWM, upper=ymax_PWM)

        self.PWM.grid(True, color='w')

        self.plot_PWM.set_xdata(np.arange(len(self.datos[PWM1])))
        self.plot_PWM.set_ydata(np.array(self.datos[PWM1]))

        self.plot_PWM2.set_xdata(np.arange(len(self.datos[PWM2])))
        self.plot_PWM2.set_ydata(np.array(self.datos[PWM2]))

        #Plot de Brujula

        xmax_Comp = len(self.datos[COMPASS]) \
        if len(self.datos[COMPASS]) > 50 else 50
        xmin_Comp = xmax_Comp - 50

        ymin_Comp = round(min(min(self.datos[COMPASS]),
         min(self.datos[COMPASSGOAL])), 0) + 1
        ymax_Comp = round(max(max(self.datos[COMPASS]),
         max(self.datos[COMPASSGOAL])), 0) + 1
        #SACAR EL MINIMO DE COMPASS Y COMPASSGOAL

        self.Brujula.set_xbound(lower=xmin_Comp, upper=xmax_Comp)
        self.Brujula.set_ybound(lower=ymin_Comp, upper=ymax_Comp)

        self.Brujula.grid(True, color='w')

        self.plot_Brujula.set_xdata(np.arange(len(self.datos[COMPASS])))
        self.plot_Brujula.set_ydata(np.array(self.datos[COMPASS]))

        self.plot_BrujulaGoal.set_xdata(np.arange(len(self.datos[COMPASSGOAL])))
        self.plot_BrujulaGoal.set_ydata(np.array(self.datos[COMPASSGOAL]))

        #Plot de Velocidades

        xmax_Vel = len(self.datos[V1]) \
        if len(self.datos[V1]) > 50 else 50

        xmin_Vel = xmax_Vel - 50

        ymin_Vel = round(min(min(self.datos[V1]), min(self.datos[V2])), 0) - 1
        ymax_Vel = round(max(max(self.datos[V1]), max(self.datos[V2])), 0) + 1

        self.Vel.set_xbound(lower=xmin_Vel, upper=xmax_Vel)
        self.Vel.set_ybound(lower=ymin_Vel, upper=ymax_Vel)

        self.Vel.grid(True, color='w')

        self.plot_Vel.set_xdata(np.arange(len(self.datos[V1])))
        self.plot_Vel.set_ydata(np.array(self.datos[V1]))

        self.plot_Vel2.set_xdata(np.arange(len(self.datos[V2])))
        self.plot_Vel2.set_ydata(np.array(self.datos[V2]))

        #Plot de POS

        xmax_POS = round(max(self.datos[POSX]), 0) - 1
        xmin_POS = round(min(self.datos[POSX]), 0) - 1

        ymin_POS = round(min(self.datos[POSY]), 0) - 1
        ymax_POS = round(max(self.datos[POSY]), 0) + 1

        self.POS.set_xbound(lower=xmin_POS, upper=xmax_POS)
        self.POS.set_ybound(lower=ymin_POS, upper=ymax_POS)

        self.POS.grid(True, color='w')

        self.plot_POS.set_xdata(np.array(self.datos[POSX]))
        self.plot_POS.set_ydata(np.array(self.datos[POSY]))

        #Dibujando Plot

        self.canvas.draw()

    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"

        dlg = wx.FileDialog(
            self,
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)

    def on_redraw_timer(self, event):

        wx.Yield()

        if not self.Pause:

            tempDatos = self.dataAQ.get()

            for i in range(15):
                self.datos[i].append(tempDatos[i])

            self.logger.AppendText(("%0.10f" % tempDatos[LATITUD])
            + "\t" + ("%0.10f" % tempDatos[LONGITUD]) + "\n")

            self.textoAltura.SetLabel(str(tempDatos[ALTITUD]))
            self.textoDistancia.SetLabel(str(tempDatos[TARGET]))
            self.textoEstado.SetLabel(str(tempDatos[ESTADO]))
            self.textoMoviendose.SetLabel(str(tempDatos[MOVIENDOSE]))
            self.textoFix.SetLabel(str(tempDatos[FIX]))

            self.draw_plot()

    def on_exit(self, event):
        self.Destroy()

    def getPath(self):
        strTime = (str(time.localtime()[0]) + "-" + str(time.localtime()[1]) +
             "-" + str(time.localtime()[2]) + "_" + str(time.localtime()[3]) +
              ":" + str(time.localtime()[4]))

        path = 'Datos_{}'.format(strTime)
        return path

    def saveData(self, event):

        #En esta funcion se van a guardar todos los datos que entran en un .txt
        #Los datos son:
        #COMPASS, PWM1, PWM2, V1, V2, LATITUD, LONGITUD, ALTITUD, COMPASSGOAL,
        #TARGET, POSX, POSY, ESTADO, MOVIENDOSE, FIX

        newpath = self.getPath()

        if not os.path.exists(newpath):
            os.makedirs(newpath)

        brujulaPath = newpath + "/datos_Brujula.txt"
        brujulaGoalPath = newpath + "/datos_BrujulaGoal.txt"
        PWM1Path = newpath + "/datos_PWM1.txt"
        PWM2Path = newpath + "/datos_PWM2.txt"
        V1Path = newpath + "/datos_V1.txt"
        V2Path = newpath + "/datos_V2.txt"
        GPSPath = newpath + "/datos_GPS.txt"
        self.GPSKMLPath = newpath + "/datos_GPS.kml"
        AltitudPath = newpath + "/datos_Altitud.txt"
        TargetPath = newpath + "/datos_Target.txt"
        PosPath = newpath + "/datos_POS.txt"
        EstadoPath = newpath + "/datos_Estado.txt"
        MoviendosePath = newpath + "/datos_Moviendose.txt"
        FixPath = newpath + "/datos_Fix.txt"

        self.fileBrujula = open(brujulaPath, 'w')
        self.fileBrujula.write("#Datos de Brujula\n")
        for i in range(len(self.datos[COMPASS])):
            txt = str(i) + '\t' + str(self.datos[COMPASS][i]) + '\n'
            self.fileBrujula.write(txt)
        self.fileBrujula.close()

        self.fileBrujulaGoal = open(brujulaGoalPath, 'w')
        self.fileBrujulaGoal.write("#Datos de BrujulaGoal\n")
        for i in range(len(self.datos[COMPASSGOAL])):
            txt = str(i) + '\t' + str(self.datos[COMPASSGOAL][i]) + '\n'
            self.fileBrujulaGoal.write(txt)
        self.fileBrujulaGoal.close()

        self.filePWM1 = open(PWM1Path, 'w')
        self.filePWM1.write("#Datos de PWM de Motor 1\n")
        for i in range(len(self.datos[PWM1])):
            txt = str(i) + '\t' + str(self.datos[PWM1][i]) + '\n'
            self.filePWM1.write(txt)
        self.filePWM1.close()

        self.filePWM2 = open(PWM2Path, 'w')
        self.filePWM2.write("#Datos de PWM de Motor 2\n")
        for i in range(len(self.datos[PWM2])):
            txt = str(i) + '\t' + str(self.datos[PWM2][i]) + '\n'
            self.filePWM2.write(txt)
        self.filePWM2.close()

        self.fileV1 = open(V1Path, 'w')
        self.fileV1.write("#Datos de velocidad del motor 1\n")
        for i in range(len(self.datos[V1])):
            txt = str(i) + '\t' + str(self.datos[V1][i]) + '\n'
            self.fileV1.write(txt)
        self.fileV1.close()

        self.fileV2 = open(V2Path, 'w')
        self.fileV2.write("#Datos de Velocidad del motor 2\n")
        for i in range(len(self.datos[V2])):
            txt = str(i) + '\t' + str(self.datos[V2][i]) + '\n'
            self.fileV2.write(txt)
        self.fileV2.close()

        self.fileAltitud = open(AltitudPath, 'w')
        self.fileAltitud.write("#Datos de Altitud dada por el barometro\n")
        for i in range(len(self.datos[ALTITUD])):
            txt = str(i) + '\t' + str(self.datos[ALTITUD][i]) + '\n'
            self.fileAltitud.write(txt)
        self.fileAltitud.close()

        self.fileTarget = open(TargetPath, 'w')
        self.fileTarget.write("#Datos de la distancia de la meta\n")
        for i in range(len(self.datos[TARGET])):
            txt = str(i) + '\t' + str(self.datos[TARGET][i]) + '\n'
            self.fileTarget.write(txt)
        self.fileTarget.close()

        self.filePOS = open(PosPath, 'w')
        self.filePOS.write("#Datos de la posicion en X y en Y\n")
        for i in range(len(self.datos[POSX])):
            txt = str(self.datos[POSX][i]) + \
            '\t' + str(self.datos[POSY][i]) + '\n'
            self.filePOS.write(txt)
        self.filePOS.close()

        self.fileEstado = open(EstadoPath, 'w')
        self.fileEstado.write("#Datos del estado del Rover\n")
        for i in range(len(self.datos[ESTADO])):
            txt = str(i) + '\t' + str(self.datos[ESTADO][i]) + '\n'
            self.fileEstado.write(txt)
        self.fileEstado.close()

        self.fileMoviendose = open(MoviendosePath, 'w')
        self.fileMoviendose.write("#Datos binarios del movimiento del Rover\n")
        for i in range(len(self.datos[MOVIENDOSE])):
            txt = str(i) + '\t' + str(self.datos[MOVIENDOSE][i]) + '\n'
            self.fileMoviendose.write(txt)
        self.fileMoviendose.close()

        self.fileFix = open(FixPath, 'w')
        self.fileFix.write("#Datos del Fix del GPS\n")
        for i in range(len(self.datos[FIX])):
            txt = str(i) + '\t' + str(self.datos[FIX][i]) + '\n'
            self.fileFix.write(txt)
        self.fileFix.close()

        self.fileGPS = open(GPSPath, 'w')
        self.fileGPS.write("#Datos del GPS\n")
        for i in range(len(self.datos[LATITUD])):
            txt = str(self.datos[LATITUD][i]) +\
             '\t' + str(self.datos[LONGITUD][i]) + '\n'
            self.fileGPS.write(txt)
        self.fileGPS.close()

        #GUARDANDO DATOS EN .KML

        kml = '<Placemark><LineString><coordinates>'

        for i in range(len(self.datosGPS[1])):
            kml += '\n' + str(self.datosGPS[1][i]) + \
            ',' + str(self.datosGPS[0][i])

        #for i in range(len(self.datos[LATITUD])):
            #kml += '\n' + str(self.datos[LONGITUD][i]) + \
                #',' + str(self.datos[LATITUD][i])

        kml += '\n </coordinates></LineString></Placemark>'

        with open(self.GPSKMLPath, 'w+') as data_file:
            data_file.write(kml)
            data_file.flush()

        self.flash_status_message("Guardado en %s" % newpath)

    def googleEarth(self, event):
        os.system("banner GOOGLE EARTH")
        command = "gnome-open " + self.GPSKMLPath
        os.system(command)

    def wxmPlotBrujula(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[COMPASS]), 1)
        self.plotframe.plot(ndato, self.datos[COMPASS], color='red',
             title='Datos Brujula')

    def wxmPlotBrujulaGoal(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[COMPASSGOAL]), 1)
        self.plotframe.plot(ndato, self.datos[COMPASSGOAL], color='red',
             title='Datos BrujulaGoal')

    def wxmPlotPWM1(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[PWM1]), 1)
        self.plotframe.plot(ndato, self.datos[PWM1], color='red',
             title='Datos PWM 1')

    def wxmPlotPWM2(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[PWM2]), 1)
        self.plotframe.plot(ndato, self.datos[PWM2], color='red',
             title='Datos PWM 2')

    def wxmPlotV1(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[V1]), 1)
        self.plotframe.plot(ndato, self.datos[V1], color='red',
             title='Datos V1')

    def wxmPlotV2(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[V2]), 1)
        self.plotframe.plot(ndato, self.datos[V2], color='red',
             title='Datos V2')

    def wxmPlotAltitud(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[ALTITUD]), 1)
        self.plotframe.plot(ndato, self.datos[ALTITUD], color='red',
             title='Datos Altitud')

    def wxmPlotTarget(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[TARGET]), 1)
        self.plotframe.plot(ndato, self.datos[TARGET], color='red',
             title='Datos distancia de la Meta')

    def wxmPlotEstado(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[ESTADO]), 1)
        self.plotframe.plot(ndato, self.datos[ESTADO], color='red',
             title='Datos Estado del Rover')

    def wxmPlotMoviendose(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[MOVIENDOSE]), 1)
        self.plotframe.plot(ndato, self.datos[MOVIENDOSE], color='red',
             title='Datos Estado del movimiento del Rover')

    def wxmPlotFix(self, event):
        self.ShowPlotFrame()
        ndato = np.arange(0, len(self.datos[FIX]), 1)
        self.plotframe.plot(ndato, self.datos[FIX], color='red',
             title='Datos del FIX del GPS')

    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER,
            self.on_flash_status_off,
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)

    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('Sensors Monitoring')


app = wx.App(redirect=False)
frame = ArlissMonitoringFrame()
frame.Show()
app.MainLoop()
