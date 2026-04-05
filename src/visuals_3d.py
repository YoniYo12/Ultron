from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight, Vec3, Vec4, GeomNode
from panda3d.core import Geom, GeomVertexData, GeomVertexFormat, GeomVertexWriter
from panda3d.core import GeomTriangles, GeomLines
from direct.task import Task
import threading


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
        """Setup camera position - the working view."""
        self.camera.setPos(0, -18, 5)
        self.camera.lookAt(0, 0, 0)
        
        self.setBackgroundColor(0.2, 0.2, 0.25, 1)
        self.camLens.setFov(75)
    
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
    
    def create_colored_cube(self):
        """Create a cube with each face a different color so rotation is obvious."""
        from panda3d.core import CardMaker
        cm = CardMaker('card')
        cm.setFrame(-1, 1, -1, 1)
        
        node = self.render.attachNewNode('cube')
        
        # Front (GREEN)
        front = node.attachNewNode(cm.generate())
        front.setPos(0, 1, 0)
        front.setColor(0.2, 1.0, 0.2, 1)
        
        # Back (RED)
        back = node.attachNewNode(cm.generate())
        back.setPos(0, -1, 0)
        back.setH(180)
        back.setColor(1.0, 0.2, 0.2, 1)
        
        # Right (BLUE)
        right = node.attachNewNode(cm.generate())
        right.setPos(1, 0, 0)
        right.setH(90)
        right.setR(90)
        right.setColor(0.2, 0.4, 1.0, 1)
        
        # Left (YELLOW)
        left = node.attachNewNode(cm.generate())
        left.setPos(-1, 0, 0)
        left.setH(-90)
        left.setR(90)
        left.setColor(1.0, 1.0, 0.2, 1)
        
        # Top (ORANGE)
        top = node.attachNewNode(cm.generate())
        top.setPos(0, 0, 1)
        top.setP(90)
        top.setColor(1.0, 0.5, 0.1, 1)
        
        # Bottom (PURPLE)
        bottom = node.attachNewNode(cm.generate())
        bottom.setPos(0, 0, -1)
        bottom.setP(-90)
        bottom.setColor(0.6, 0.2, 1.0, 1)
        
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
        """Load colored cube - each face different color so rotation is visible."""
        self.objects = []
        
        cube = self.create_colored_cube()
        cube.reparentTo(self.render)
        cube.setPos(0, 0, 0)
        # Uniform scale — thin Z made the cube disappear when roll() turned it edge-on
        self.base_scale = 0.65
        cube.setScale(self.base_scale, self.base_scale, self.base_scale)
        cube.setTwoSided(True)
        
        self.objects.append({'model': cube, 'name': 'Cube', 'base_scale': self.base_scale})
        
        # Set as the active model
        self.selected_index = 0
        self.model = self.objects[self.selected_index]['model']
        
        # State
        self.rotation_speed = 40
        self.auto_rotate = True
        
        # Grab-rotate: movement-based spin (tangential velocity around screen center)
        self._prev_rotating = False
        self.target_r = 0.0
        self.smoothed_r = 0.0
        
        print("="*50)
        print("Colored cube loaded!")
        print("  Front=Green, Back=Red, Right=Blue")
        print("  Left=Yellow, Top=Orange, Bottom=Purple")
        print(f"Position: {self.model.getPos()}")
        print(f"Scale: {self.model.getScale()}")
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
            self._prev_rotating = False
            if self.auto_rotate:
                current_h = self.model.getH()
                self.model.setH(current_h + self.rotation_speed * globalClock.getDt())
            return Task.cont
        
        is_active = control.get('is_active', False)
        is_rotating = control.get('is_rotating', False)
        position = control.get('position', [0.5, 0.5, 0.0])
        
        if is_rotating:
            # GRAB: rotation from smoothed hand *movement* (mapper deltas), not atan2(center).
            # Tangential term: r × v in 2D (clockwise motion around center → roll).
            self.auto_rotate = False
            
            if not self._prev_rotating:
                self.target_r = self.model.getR()
                self.smoothed_r = self.target_r
            self._prev_rotating = True
            
            gd = control.get('grab_delta_xy', [0.0, 0.0])
            gp = control.get('grab_position', [0.5, 0.5, 0.0])
            dx, dy = gd[0], gd[1]
            gx, gy = gp[0], gp[1]
            rx = gx - 0.5
            ry = gy - 0.5
            omega = rx * dy - ry * dx
            spin = omega * 2200.0
            spin -= dx * 520.0
            # Cap per-frame spin so noise doesn't roll the cube edge-on (invisible)
            max_spin = 12.0
            spin = max(-max_spin, min(max_spin, spin))
            
            self.target_r += spin
            self.smoothed_r += (self.target_r - self.smoothed_r) * 0.42
            self.model.setR(self.smoothed_r)
            self.model.setScale(self.base_scale, self.base_scale, self.base_scale)
            
            self.model.setColor(1.0, 0.6, 0.1, 1.0)
            self.model.setColorScale(1.3, 1.3, 1.3, 1.0)
            self.status_text.setText("ROTATING - move hand in an arc")
            
        elif is_active:
            # PINCH: Move the object
            self.auto_rotate = False
            self._prev_rotating = False
            
            x = (position[0] - 0.5) * 6
            z = (0.5 - position[1]) * 4
            y = position[2] * -2
            
            self.model.setPos(x, y, z)
            self.model.setScale(self.base_scale, self.base_scale, self.base_scale)
            self.model.setColor(0.2, 1.0, 0.2, 1.0)
            self.model.setColorScale(1.5, 1.5, 1.5, 1.0)
            self.status_text.setText("PINCH - Move hand to translate")
            
        else:
            # RELEASED: Hold position and rotation
            self._prev_rotating = False
            self.model.setScale(self.base_scale, self.base_scale, self.base_scale)
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