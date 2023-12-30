import tkinter as tk
from tkinter import ttk, filedialog
import time
from threading import Thread
import math
import pickle

lastTime = time.time()

def rgb_to_hex(color: tuple[int, int, int]):
    return '#{:02x}{:02x}{:02x}'.format(*color)

def lerp_color(color1, color2, t):
    """
    Perform linear interpolation between two colors.

    Parameters:
    - color1: Tuple representing the RGB values of the first color.
    - color2: Tuple representing the RGB values of the second color.
    - t: Interpolation parameter (0 to 1).

    Returns:
    - Tuple representing the interpolated color.
    """
    r = int(color1[0] + (color2[0] - color1[0]) * t)
    g = int(color1[1] + (color2[1] - color1[1]) * t)
    b = int(color1[2] + (color2[2] - color1[2]) * t)

    return (r, g, b)

def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

class Connector:
    def __init__(self, name, temp:float = 0.0, flowSpeed:float = 1.0):
        self.name = name
        self.connectedTo = None
        self.temp = temp 
        self.flowSpeed = flowSpeed
    
class LogicConnector:
    def __init__(self, value:bool = 0.0):
        self.connectedTo = []
        self.value = value
    

class Component:
    def __init__(self, name, x, y, inputs: list[Connector] = [], outputs: list[Connector] = [], logicInput: LogicConnector = None, logicOutput: LogicConnector = None):
        self.name = name
        self.x = x
        self.y = y
        self.width = 120
        self.height = 50
        self.inputs = inputs
        self.outputs = outputs
        self.connectors = inputs + outputs
        self.logicInput = logicInput
        self.logicOutput = logicOutput
        self.logicConnectors = [logicInput, logicOutput]

    def inspect(self, childDict:dict = {}) -> dict[str, str]:
        inspectables = {}
        inspectables["name"] = self.name
        inspectables.update(childDict)
        return inspectables

    def editVariable(self, varName, value):
        match varName:
            case "name":
                self.name = value
            case "power":
                self.power = float(value)
            case "temp":
                self.temp = float(value)
            case "speed":
                self.speed = float(value)
            case _:
                print("No match")

    def getConnectorPosition(self, connector: Connector):
        if connector not in self.connectors:
            return None

        if connector in self.inputs:
            relativeX = (self.inputs.index(connector) + 1) * self.width / (len(self.inputs) + 1)
            relativeY = -self.height / 2
        elif connector in self.outputs:
            relativeX = (self.outputs.index(connector) + 1) * self.width / (len(self.outputs) + 1)
            relativeY = self.height / 2

        return self.x - (self.width / 2) + relativeX, self.y + relativeY
    
    def getConnector(self, x, y):
        for connector in self.connectors:
            connectorX, connectorY = self.getConnectorPosition(connector)
            if abs(connectorX - x) < 5 and abs(connectorY - y) < 5:
                return connector
        return None
    
    def getLogicConnectorPosition(self, connector: LogicConnector):
        if connector not in [self.logicInput, self.logicOutput]:
            return None

        if connector == self.logicInput:
            relativeX = -self.width / 2
            relativeY = 0
        elif connector == self.logicOutput:
            relativeX = self.width / 2
            relativeY = 0

        return self.x + relativeX, self.y + relativeY
    
    def getLogicConnector(self, x, y):
        for connector in self.logicConnectors:
            connectorX, connectorY = self.getLogicConnectorPosition(connector)
            if abs(connectorX - x) < 5 and abs(connectorY - y) < 5:
                return connector
        return None
    
    def update(self):
        for input in self.inputs:
            if input.connectedTo is None:
                continue

            input.temp = input.connectedTo.temp
            input.flowSpeed = input.connectedTo.flowSpeed

        if self.logicInput is not None:
            if len(self.logicInput.connectedTo) == 0:
                self.logicInput.value = 0
                return
            self.logicInput.value = self.logicInput.connectedTo[0].value
    
# Temperature functions

def calculateDeltaT(
        Power: float,
        stroomSnelheid: float,
        sortWarmte: float = 4.18):
    """
    Calculates the delta T for a given warmte and power
    """
    dT = (Power / sortWarmte) / stroomSnelheid
    return dT

# Flow Code

class SinusSignal(Component):
    def __init__(self, name, x, y, period):
        self.period = period
        super().__init__(
            name, 
            x, 
            y,
            logicOutput=LogicConnector()
        )

    def inspect(self) -> dict[str, str]:
        return super().inspect({
            "period": self.period
        })
            
    def editVariable(self, varName, value):
        match varName:
            case "period":
                self.period = float(value)
            case _:
                super().editVariable(varName, value)

    def update(self):
        super().update()
        self.logicOutput.value = math.sin(time.time() * 2 * math.pi / self.period)/2 + 0.5

class Source(Component):
    def __init__(self, name, x, y, maxTemp, speed):
        self.maxTemp = maxTemp
        self.speed = speed
        super().__init__(
            name, 
            x, 
            y,
            outputs = [Connector("OUT", maxTemp, speed)],
            logicInput=LogicConnector()
        )

    def inspect(self) -> dict[str, str]:
        return super().inspect({
            "maxTemp": self.maxTemp,
            "speed": self.speed
        })
        
    def editVariable(self, varName, value):
        match varName:
            case "maxTemp":
                self.maxTemp = float(value)
            case "speed":
                self.speed = float(value)
            case _:
                super().editVariable(varName, value)

    def update(self):
        super().update()
        if self.logicInput.connectedTo is not None:
            self.outputs[0].temp = self.maxTemp * self.logicInput.value
        else:
            self.outputs[0].temp = self.maxTemp
        self.outputs[0].flowSpeed = self.speed

class Printer(Component):
    def __init__(self, name, x, y):
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT")]
        )

    def update(self):
        super().update()
        self.outputs[0].temp = self.inputs[0].temp
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed
        print(f"{self.name}:" ,self.inputs[0].temp, self.inputs[0].flowSpeed)

class Process(Component):
    def __init__(self, name, x, y, power, minTemp = 0):
        self.power = power
        self.minTemp = minTemp
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT")],
            logicInput=LogicConnector()
        )

    def inspect(self) -> dict[str, str]:
        return super().inspect({
            "power": self.power,
            "minTemp": self.minTemp
        })
    
    def editVariable(self, varName, value):
        match varName:
            case "power":
                self.power = float(value)
            case "minTemp":
                self.minTemp = float(value)
            case _:
                super().editVariable(varName, value)
            
    

    def update(self):
        super().update()
        scalar = 1 if self.logicInput.connectedTo == [] else self.logicInput.value
        if self.inputs[0].temp < self.minTemp:
            self.outputs[0].temp = self.inputs[0].temp
        else:
            self.outputs[0].temp = self.inputs[0].temp + calculateDeltaT(self.power * scalar, 1)
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed

class Buffer(Component):
    def __init__(self, name, x, y, maxTemp, capacity):
        self.maxTemp = maxTemp
        self.capacity = capacity
        self.temp = 0
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT")],
        )

    def inspect(self) -> dict[str, str]:
        return super().inspect({
            "maxTemp": self.maxTemp,
            "capacity": self.capacity
        })
    
    def editVariable(self, varName, value):
        match varName:
            case "maxTemp":
                self.maxTemp = float(value)
            case "capacity":
                self.capacity = float(value)
            case _:
                super().editVariable(varName, value)

    def update(self):
        super().update()
        
        VolumeIn = self.inputs[0].flowSpeed * (time.time() - lastTime)
        self.temp = (VolumeIn * self.inputs[0].temp + self.temp * self.capacity) / (VolumeIn + self.capacity)

        self.outputs[0].temp = self.temp
        self.outputs[0].flowSpeed = self.inputs[0].flowSpeed


class Splitter(Component):
    def __init__(self, name, x, y, splitScalar):
        self.splitScalar = splitScalar
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN")],
            outputs = [Connector("OUT1"), Connector("OUT2")],
            logicInput=LogicConnector()
        )

    def inspect(self) -> dict[str, str]:
        return super().inspect({
            "splitScalar": self.splitScalar
        })
    
    def editVariable(self, varName, value):
        match varName:
            case "splitScalar":
                self.splitScalar = float(value)
            case _:
                super().editVariable(varName, value)

    def update(self):
        super().update()
        self.outputs[0].temp = self.inputs[0].temp
        self.outputs[1].temp = self.inputs[0].temp

        if self.logicInput.connectedTo == []:
            self.outputs[0].flowSpeed = self.inputs[0].flowSpeed * self.splitScalar
            self.outputs[1].flowSpeed = self.inputs[0].flowSpeed * (1 - self.splitScalar)
        else:
            self.outputs[0].flowSpeed = self.inputs[0].flowSpeed * self.logicInput.value
            self.outputs[1].flowSpeed = self.inputs[0].flowSpeed * (1 - self.logicInput.value)

class Merge(Component):
    def __init__(self, name, x, y):
        super().__init__(
            name, 
            x, 
            y,
            inputs = [Connector("IN1"), Connector("IN2")],
            outputs = [Connector("OUT")]
        )

    def update(self):
        super().update()
        flowSpeed1 = self.inputs[0].flowSpeed
        flowSpeed2 = self.inputs[1].flowSpeed
        temp1 = self.inputs[0].temp
        temp2 = self.inputs[1].temp

        self.outputs[0].temp = (flowSpeed1 * temp1 + flowSpeed2 * temp2) / (flowSpeed1 + flowSpeed2)
        self.outputs[0].flowSpeed = (self.inputs[0].flowSpeed + self.inputs[1].flowSpeed)

# UI Code

class ConnectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Flow Diagram")

        self.components = []
        self.selected_output = None

        self.canvas = tk.Canvas(root, width=800, height=800, bg="white")
        self.canvas.pack()

        self.menuBar = tk.Menu(root)
        self.fileMenu = tk.Menu(self.menuBar, tearoff=0)
        self.fileMenu.add_command(label="New", command=self.clearFlow)
        self.fileMenu.add_command(label="Open", command=self.loadFlow)
        self.fileMenu.add_command(label="Save as...", command=self.saveFlow)
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label="Exit", command=root.quit)
        self.menuBar.add_cascade(label="File", menu=self.fileMenu)

        self.addComponentMenu = tk.Menu(self.menuBar, tearoff=0)

        self.basicComponentsMenu = tk.Menu(self.addComponentMenu, tearoff=0)
        self.basicComponentsMenu.add_command(label="Source", command=lambda: self.add_component("Source", 120, 70))
        self.basicComponentsMenu.add_command(label="Printer", command=lambda: self.add_component("Printer", 120, 70))
        self.basicComponentsMenu.add_command(label="Process", command=lambda: self.add_component("Process", 120, 70))
        self.basicComponentsMenu.add_command(label="Buffer", command=lambda: self.add_component("Buffer", 120, 70))
        self.addComponentMenu.add_cascade(label="BasicComponents", menu=self.basicComponentsMenu)

        self.verdelingsMenu = tk.Menu(self.addComponentMenu, tearoff=0)
        self.verdelingsMenu.add_command(label="Splitter", command=lambda: self.add_component("Splitter", 120, 70))
        self.verdelingsMenu.add_command(label="Merge", command=lambda: self.add_component("Merge", 120, 70))
        self.addComponentMenu.add_cascade(label="Verdeling", menu=self.verdelingsMenu)

        self.logicComponentsMenu = tk.Menu(self.addComponentMenu, tearoff=0)
        self.logicComponentsMenu.add_command(label="SinusSignal", command=lambda: self.add_component("SinusSignal", 120, 70))
        self.addComponentMenu.add_cascade(label="LogicComponents", menu=self.logicComponentsMenu)

        self.menuBar.add_cascade(label="AddComponent", menu=self.addComponentMenu)

        self.root.config(menu=self.menuBar)
        
        self.menu = tk.Frame(root)
        self.menu.pack()

        self.stopCommand = False

        self.startButton = ttk.Button(self.menu, text="Start", command=lambda: Thread(target=self.update).start())
        self.startButton.grid(row=0, column=0)

        self.stopButton = ttk.Button(self.menu, text="Stop", command=self.stopLoop )
        self.stopButton.grid(row=0, column=6)

        self.addComponent = ttk.Button(self.menu, text="Add Component", command=lambda: self.add_component("Component", 120, 70))
        self.addComponent.grid(row=0, column=1)

        self.addSource = ttk.Button(self.menu, text="Add Source", command=lambda: self.add_component("Source", 120, 70))
        self.addSource.grid(row=0, column=2)

        self.addPrinter = ttk.Button(self.menu, text="Add Printer", command=lambda: self.add_component("Printer", 120, 70))
        self.addPrinter.grid(row=0, column=3)

        self.addProcess = ttk.Button(self.menu, text="Add Process", command=lambda: self.add_component("Process", 120, 70))
        self.addProcess.grid(row=0, column=4)

        self.addProcess = ttk.Button(self.menu, text="Add Splitter", command=lambda: self.add_component("Splitter", 120, 70))
        self.addProcess.grid(row=0, column=5)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        self.firstConnector = None

        

    def stopLoop(self):
        self.stopCommand = True

    def clearFlow(self):
        self.components = []
        self.redraw_canvas()

    def saveFlow(self):
        file_path = filedialog.asksaveasfile(mode="wb", defaultextension=".flow", filetypes=[("HeatFlow files", "*.flow")], initialdir="flows", initialfile="myHeatFlow.flow")
        if file_path is None:
            return
        pickle.dump(self.components, file_path)
        file_path.close()

    def loadFlow(self):
        file_path = filedialog.askopenfile(mode="rb", defaultextension=".flow", filetypes=[("HeatFlow files", "*.flow")], initialdir="flows")
        if file_path is None:
            return
        self.components = pickle.load(file_path)
        file_path.close()
        self.redraw_canvas()
    
    def openInspector(self, component):
        inspector = tk.Toplevel(self.root)
        inspector.geometry("750x250")
        inspector.title(f"Inspector - {component.name}")

        variables = {}

        for i, key in enumerate(dict(component.inspect())):
            value = dict(component.inspect())[key]
            ttk.Label(inspector, text=f"{key}:").place(x=10,y=10 + i*30)
            entery = ttk.Entry(
                inspector, 
                width=20, 
            )
            entery.delete(0, tk.END)
            entery.insert(0, str(value))
            variables[key] = entery
            entery.place(x=90,y=10 + i*30)

        def updateVariables():
            for key, entery in variables.items():
                component.editVariable(key, entery.get())
            self.redraw_canvas()

        ttk.Button(inspector, text="Update", command=updateVariables).place(anchor=tk.SE, x=740, y=210)

        ttk.Button(inspector, text="Close", command=inspector.destroy).place(anchor=tk.SE, x=740, y=240)


    def add_component(self, name, x, y, inputs: list[Connector] = [Connector("IN")], outputs: list[Connector] = [Connector("OUT")]):
        match name:
            case "Source":
                component = Source(name, x, y, 100, 1)
            case "Printer":
                component = Printer(name, x, y)
            case "Process":
                component = Process(name, x, y, 100)
            case "Splitter":
                component = Splitter(name, x, y, 0.5)
            case "SinusSignal":
                component = SinusSignal(name, x, y, 10)
            case "Merge":
                component = Merge(name, x, y)
            case "Buffer":
                component = Buffer(name, x, y, 100, 100)
            case _:
                component = Component(name, x, y, inputs, outputs)
        self.components.append(component)
        self.draw_component(component)

    

    def draw_component(self, component):
        self.canvas.create_rectangle(
            component.x - component.width / 2, component.y - component.height / 2,
            component.x + component.width / 2, component.y + component.height / 2,
            fill="lightblue"
        )
        self.canvas.create_text(
            component.x, component.y,
            text=component.name
        )

        for logicConnector in component.logicConnectors:
            if logicConnector is None:
                continue
            connectorX, connectorY = component.getLogicConnectorPosition(logicConnector)

            self.canvas.create_oval(
                connectorX - 3,
                connectorY - 3,
                connectorX + 3,
                connectorY + 3,
                fill="lightgreen"
            )

        for connector in component.connectors:
            connectorX, connectorY = component.getConnectorPosition(connector)

            self.canvas.create_text(
                connectorX,
                connectorY + (3 if connector in component.inputs else -3),
                text=connector.name,
                anchor= (tk.N if connector in component.inputs else tk.S)
            )

            self.canvas.create_oval(
                connectorX - 3,
                connectorY - 3,
                connectorX + 3,
                connectorY + 3,
                fill="blue"
            )

    def connect_components(self, fromConnector: Connector, toConnector: Connector):
        if isinstance(fromConnector, LogicConnector):
            if fromConnector in toConnector.connectedTo:
                toConnector.connectedTo.remove(fromConnector)
                fromConnector.connectedTo.remove(toConnector)
            else:
                toConnector.connectedTo.append(fromConnector)
                fromConnector.connectedTo.append(toConnector)
            self.draw_logic_connector([fromConnector, toConnector])
            return
        
        fromConnector.connectedTo = toConnector
        toConnector.connectedTo = fromConnector
        self.redraw_canvas()


    def draw_connector(self, connectors:list[Connector]):
        connector1X, connector1Y = self.getConnectorPosition(connectors[0])
        connector2X, connector2Y = self.getConnectorPosition(connectors[1])
        flowSpeed = connectors[0].flowSpeed
        temp = connectors[0].temp

        self.canvas.create_line(
            connector1X, 
            connector1Y, 
            connector2X, 
            connector2Y,
            arrow=tk.LAST,
            fill=rgb_to_hex(lerp_color((0, 0, 255), (255, 0, 0), clamp(temp / 100, 0, 1))),
            width=flowSpeed * 4,
            tags="connector"
        )

    def draw_logic_connector(self, connectors:list[LogicConnector]):
        connector1X, connector1Y = self.getConnectorPosition(connectors[0])
        connector2X, connector2Y = self.getConnectorPosition(connectors[1])
        value = connectors[0].value

        self.canvas.create_line(
            connector1X, 
            connector1Y, 
            connector2X, 
            connector2Y,
            arrow=tk.LAST,
            fill=rgb_to_hex(lerp_color((0, 255, 0), (0, 100, 0), value)),
            width=4,
            tags="connector"
        )


    def on_canvas_click(self, event):
        connector = self.getConnector(event.x, event.y)
        if connector is not None:
            if self.firstConnector is None:
                self.firstConnector = connector
            else:
                self.connect_components(self.firstConnector, connector)
                self.firstConnector = None
    
    def on_canvas_right_click(self, event):
        self.openInspector(self.getComponent(event.x, event.y))

    def getConnector(self, x, y):
        for component in self.components:
            connector = component.getConnector(x, y)
            if connector is None:
                connector = component.getLogicConnector(x, y)
            if connector is not None:
                return connector
        return None
    
    def getComponent(self, x, y):
        for component in self.components:
            if (
                component.x - component.width / 2 <= x <= component.x + component.width / 2 and
                component.y - component.height / 2 <= y <= component.y + component.height / 2
            ):
                return component
        return None
    
    def getConnectorPosition(self, connector: Connector):
        for component in self.components:
            connectorPosition = component.getConnectorPosition(connector)
            if connectorPosition is None:
                connectorPosition = component.getLogicConnectorPosition(connector)
            if connectorPosition is not None:
                return connectorPosition
        return None

    def on_drag(self, event):
        for component in self.components:
            if (
                component.x - component.width / 2 <= event.x <= component.x + component.width / 2 and
                component.y - component.height / 2 <= event.y <= component.y + component.height / 2
            ):
                component.x = round(event.x, -1)
                component.y = round(event.y, -1)
                self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        for component in self.components:
            self.draw_component(component)

            if component.logicOutput is not None:
                for logicConnector in component.logicOutput.connectedTo:
                    self.draw_logic_connector([component.logicOutput, logicConnector])

            for output in component.outputs:
                if output.connectedTo is None:
                    continue

                self.draw_connector([output, output.connectedTo])

    def redraw_connector(self):
        self.canvas.addtag_withtag("old", "connector")

        for component in self.components:
            if component.logicOutput is not None:
                for logicConnector in component.logicOutput.connectedTo:
                    self.draw_logic_connector([component.logicOutput, logicConnector])

            for output in component.outputs:
                if output.connectedTo is None:
                    continue

                self.draw_connector([output, output.connectedTo])
        self.canvas.delete("old")

    def update(self):
        while not self.stopCommand:
            for component in self.components:
                component.update()
            self.redraw_connector()
            lastTime = time.time()
            time.sleep(0.1)
        self.stopCommand = False
        
        

if __name__ == "__main__":
    root = tk.Tk()
    app = ConnectorApp(root)

    root.mainloop()
