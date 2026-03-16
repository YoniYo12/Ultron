from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight, Vec3, Vec4, GeomNode
from panda3d.core import Geom, GeomVertexData, GeomVertexFormat, GeomVertexWriter
from panda3d.core import GeomTriangles, GeomLines
from direct.task import Task
import threading
import math


class HandControlled3DApp(ShowBase):
    """Panda3D application for 3D object manipulation with hand tracking."""
    
    def __init__(self, control_data_ref):
        """
        Initialize Panda3D window and 3D scene.
        
        Args:zz
            control_data_ref: Shared dict for control data from tracking thread
        """
        super().__init__()
        
        # Set window title
        from panda3d.core import WindowProperties
        props = WindowProperties()
        props.setTitle("Ultron - Hand Controlled 3D")
        self.win.requestProperties(props)
        
        # Shared control data from tracking thread
        self.control_data = control_data_ref
        
        # Setup scene
        self.setup_camera()
        self.setup_lighting()
        self.load_model()
        
        # Add update task
        self.taskMgr.add(self.update_task, "UpdateTask")
        
        # Display instructions
        self.setup_ui()
    
    def setup_camera(self):
        """Setup camera position."""
        self.camera.setPos(0, -10, 3)
        self.camera.lookAt(0, 0, 0)
        
        self.setBackgroundColor(0.15, 0.15, 0.2, 1)
        self.camLens.setFov(60)
    
    def setup_lighting(self):
        """Setup scene lighting."""
        # Very bright ambient light
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.8, 0.8, 0.8, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)
        
        # Directional light from front
        directional1 = DirectionalLight("directional1")
        directional1.setColor(Vec4(1.0, 1.0, 1.0, 1))
        directional_np1 = self.render.attachNewNode(directional1)
        directional_np1.setHpr(0, -30, 0)
        self.render.setLight(directional_np1)
        
        # Add reference grid
        self.create_grid()
    
    def create_grid(self):
        """Create a reference grid on the ground."""
        from panda3d.core import LineSegs
        
        lines = LineSegs()
        lines.setThickness(2)
        lines.setColor(0.4, 0.4, 0.5, 1)
        
        # Grid lines (smaller, below cube)
        for i in range(-6, 7, 2):
            # Lines parallel to X axis
            lines.moveTo(i, -6, -2)
            lines.drawTo(i, 6, -2)
            # Lines parallel to Y axis
            lines.moveTo(-6, i, -2)
            lines.drawTo(6, i, -2)
        
        grid_node = self.render.attachNewNode(lines.create())
    
    def create_3d_cross(self):
        """Create a 3D cross with colored arms so rotation is obvious."""
        from panda3d.core import CardMaker
        
        node = self.render.attachNewNode('cross')
        
        cm = CardMaker('bar')
        bar_length = 1.0
        bar_thickness = 0.25
        
        # X axis bar (RED) - horizontal
        cm.setFrame(-bar_length, bar_length, -bar_thickness, bar_thickness)
        x_front = node.attachNewNode(cm.generate())
        x_front.setColor(1, 0.2, 0.2, 1)
        x_back = node.attachNewNode(cm.generate())
        x_back.setH(180)
        x_back.setColor(1, 0.2, 0.2, 1)
        x_top = node.attachNewNode(cm.generate())
        x_top.setP(90)
        x_top.setColor(0.8, 0.15, 0.15, 1)
        x_bottom = node.attachNewNode(cm.generate())
        x_bottom.setP(-90)
        x_bottom.setColor(0.8, 0.15, 0.15, 1)
        
        # Y axis bar (BLUE) - depth
        cm.setFrame(-bar_thickness, bar_thickness, -bar_thickness, bar_thickness)
        for angle in [0, 90, 180, 270]:
            face = node.attachNewNode(cm.generate())
            face.setPos(0, 0, 0)
            face.setH(angle)
            face.setScale(1, bar_length, 1)
            face.setColor(0.2, 0.4, 1.0, 1)
        
        # Z axis bar (GREEN) - vertical
        cm.setFrame(-bar_thickness, bar_thickness, -bar_length, bar_length)
        z_front = node.attachNewNode(cm.generate())
        z_front.setColor(0.2, 1, 0.3, 1)
        z_back = node.attachNewNode(cm.generate())
        z_back.setH(180)
        z_back.setColor(0.2, 1, 0.3, 1)
        z_left = node.attachNewNode(cm.generate())
        z_left.setH(90)
        z_left.setColor(0.15, 0.8, 0.2, 1)
        z_right = node.attachNewNode(cm.generate())
        z_right.setH(-90)
        z_right.setColor(0.15, 0.8, 0.2, 1)
        
        # Small center cube to anchor visually
        cm.setFrame(-bar_thickness*1.5, bar_thickness*1.5, -bar_thickness*1.5, bar_thickness*1.5)
        for angle in [0, 90, 180, 270]:
            c = node.attachNewNode(cm.generate())
            c.setH(angle)
            c.setColor(1, 1, 1, 1)
        c_top = node.attachNewNode(cm.generate())
        c_top.setP(90)
        c_top.setColor(1, 1, 1, 1)
        c_bot = node.attachNewNode(cm.generate())
        c_bot.setP(-90)
        c_bot.setColor(1, 1, 1, 1)
        
        return node
    
    def create_sphere(self, segments=20):
        """Create a procedural sphere using UV coordinates."""
        from panda3d.core import NodePath
        node = NodePath('sphere')
        
        # Use smiley model as sphere (it's a built-in that usually exists)
        try:
            sphere = self.loader.loadModel("smiley")
            sphere.reparentTo(node)
        except:
            # Fallback: create icosphere-like shape
            node = self.create_cube()
        
        return node
    
    def load_model(self):
        """Load 3D cross model - rotation is obvious from any angle."""
        self.objects = []
        
        cross = self.create_3d_cross()
        cross.reparentTo(self.render)
        cross.setPos(0, 0, 0)
        cross.setScale(2.0)
        cross.setTwoSided(True)
        
        self.objects.append({'model': cross, 'name': 'Cross', 'base_scale': 2.0})
        
        # Set as the active model
        self.selected_index = 0
        self.model = self.objects[self.selected_index]['model']
        
        # State
        self.rotation_speed = 40
        self.auto_rotate = True
        
        # Grab-rotate tracking (SpaceX style)
        self.grab_active = False
        self.grab_start_pos = [0.5, 0.5]
        self.grab_start_h = 0.0
        self.grab_start_p = 0.0
        
        from panda3d.core import TextNode
        text3d = TextNode('label')
        text3d.setText('R=Red  G=Green  B=Blue')
        text3d_node = self.render.attachNewNode(text3d)
        text3d_node.setScale(0.3)
        text3d_node.setPos(-1.5, 0, 2.5)
        text3d_node.setBillboardPointEye()
        
        print("="*50)
        print("3D Cross loaded!")
        print("  Red bar   = X axis (horizontal)")
        print("  Green bar = Z axis (vertical)")
        print("  Blue bar  = Y axis (depth)")
        print("  White center cube")
        print(f"Position: {self.model.getPos()}")
        print(f"Camera: {self.camera.getPos()}")
        print("="*50)
    
    
    def setup_ui(self):
        """Setup on-screen text instructions."""
        from direct.gui.OnscreenText import OnscreenText
        
        self.title_text = OnscreenText(
            text="ULTRON - Hand Control",
            pos=(0, 0.9),
            scale=0.08,
            fg=(0.2, 0.8, 1.0, 1),
            shadow=(0, 0, 0, 1)
        )
        
        self.status_text = OnscreenText(
            text="Waiting for hand...",
            pos=(-1.3, -0.9),
            scale=0.05,
            fg=(1, 1, 0, 1),
            align=0
        )
        
        self.controls_text = OnscreenText(
            text="CONTROLS:\n\n  Pinch = Grab & Move\n  Close Hand = Grab & Rotate\n  Open Hand = Release\n\nPress ESC to quit",
            pos=(-1.3, 0.8),
            scale=0.055,
            fg=(0.8, 0.8, 0.8, 1),
            align=0
        )
    
    def update_task(self, task):
        """
        Per-frame update task.
        Pinch = grab and move (translate).
        Grab (closed hand) = grab and rotate (SpaceX style: hand movement = rotation).
        """
        control = self.control_data.get('latest', None)
        
        if control is None:
            self.status_text.setText("Waiting for hand...")
            self.grab_active = False
            if self.auto_rotate:
                current_h = self.model.getH()
                self.model.setH(current_h + self.rotation_speed * globalClock.getDt())
            return Task.cont
        
        is_active = control.get('is_active', False)
        is_rotating = control.get('is_rotating', False)
        raw_pos = control.get('raw_position', [0.5, 0.5, 0.0])
        position = control.get('position', [0.5, 0.5, 0.0])
        
        if is_rotating:
            # GRAB: Rotate object by moving hand (SpaceX/Iron Man style)
            self.auto_rotate = False
            
            if not self.grab_active:
                # Grab just started - snapshot starting state
                self.grab_start_pos = [raw_pos[0], raw_pos[1]]
                self.grab_start_h = self.model.getH()
                self.grab_start_p = self.model.getP()
                self.grab_active = True
            
            # Hand movement delta from grab start → object rotation
            dx = raw_pos[0] - self.grab_start_pos[0]  # horizontal movement
            dy = raw_pos[1] - self.grab_start_pos[1]  # vertical movement
            
            # Map hand movement to rotation (300 deg per full screen width)
            rotation_sensitivity = 300.0
            new_h = self.grab_start_h - dx * rotation_sensitivity
            new_p = self.grab_start_p + dy * rotation_sensitivity
            
            self.model.setH(new_h)
            self.model.setP(new_p)
            
            # Orange glow when rotating
            self.model.setColor(1.0, 0.6, 0.1, 1.0)
            self.model.setColorScale(1.3, 1.3, 1.3, 1.0)
            self.status_text.setText("ROTATING - Move hand to spin object")
            
        elif is_active:
            # PINCH: Move the object
            self.auto_rotate = False
            self.grab_active = False
            
            x = (position[0] - 0.5) * 6
            z = (0.5 - position[1]) * 4
            y = position[2] * -2
            
            self.model.setPos(x, y, z)
            self.model.setScale(2.0)
            self.model.setColor(0.2, 1.0, 0.2, 1.0)
            self.model.setColorScale(1.5, 1.5, 1.5, 1.0)
            self.status_text.setText("PINCH - Move hand to translate")
            
        else:
            # RELEASED: Hold position and rotation
            self.grab_active = False
            self.model.setColorScale(1, 1, 1, 1)
            self.model.setColor(0.3, 0.8, 0.3, 1.0)
            self.status_text.setText("OPEN - Object held in place")
            
            if self.auto_rotate:
                current_h = self.model.getH()
                self.model.setH(current_h + self.rotation_speed * globalClock.getDt())
        
        return Task.cont


def run_3d_app(control_data_ref):
    """
    Run the Panda3D application.
    
    Args:
        control_data_ref: Shared dictionary for control data
    """
    app = HandControlled3DApp(control_data_ref)
    app.run()


if __name__ == "__main__":
    # Test with dummy data
    import time
    
    control_data = {
        'latest': {
            'is_active': False,
            'pinch_strength': 0.5,
            'position': [0.5, 0.5, 0.0]
        }
    }
    
    # Start 3D app
    print("Starting Panda3D...")
    print("This is a test mode with dummy data.")
    print("Run run_tracking.py for real hand control!")
    
    app = HandControlled3DApp(control_data)
    
    # Simulate hand control after 3 seconds
    def simulate_control(task):
        if task.time > 3:
            control_data['latest'] = {
                'is_active': True,
                'pinch_strength': 0.7,
                'position': [0.6, 0.4, 0.0]
            }
        return Task.cont
    
    app.taskMgr.add(simulate_control, "SimulateControl")
    app.run()