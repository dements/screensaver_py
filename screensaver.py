import pygame
import random
import numpy as np
from typing import List, Tuple
import sys
import traceback
import math
import pygame_gui

# =============================================================================
# CONFIGURATION - Adjust these parameters to modify the simulation
# =============================================================================

# Drop Settings
DROP_MIN_SIZE = 3          # Minimum size of water drops
DROP_MAX_SIZE = 5          # Maximum size of water drops
DROP_SPEED_FACTOR = 0.02   # How much size affects drop speed (bigger = faster)
DROP_STRETCH_FACTOR = 0.3  # How much drops stretch when moving
DROP_SPAWN_RATE = 10       # Frames between drop spawns (lower = more drops)
DROP_CLUSTER_SIZE = (1, 3) # Min and max drops per cluster
DROP_CLUSTER_SPREAD = 20   # How far drops spread in a cluster
DROP_COLLISION_FACTOR = 0.7 # How easily drops merge (> 1.0 means merge before touching)

# Surface Tension Settings
SURFACE_TENSION = 0.3      # Surface tension strength (0-1)
TENSION_ROUNDNESS = 0.6    # How round drops try to stay (0-1)
TENSION_MERGE_THRESHOLD = 0.3  # How likely drops are to merge when touching (0-1)
TENSION_BREAK_POINT = 1.0  # How much stretching before a drop breaks
TENSION_WOBBLE = 0.4       # How much drops wobble when moving

# Movement Settings
RANDOM_MOVEMENT = 0.1      # How much drops randomly move sideways (0-1)
MOMENTUM_FACTOR = 0.2     # How much drops maintain their direction (0-1)
WIND_EFFECT = 0.01         # Base sideways movement tendency (positive = right, negative = left)

# Canal Settings
CANAL_GRID_SIZE = 10        # Grid size for canal formation (bigger = fewer canals)
CANAL_MAX_WIDTH = 4.0      # Maximum width of canals
CANAL_ALPHA = 20          # Base canal visibility (0-255)
CANAL_GROWTH_RATE = 0.01   # How fast canals strengthen
CANAL_WIDTH_GROWTH = 0.2   # How fast canals widen
CANAL_STRENGTH_INCREASE = 0.5 # How much each drop adds to canal strength

# Canal Influence on Drops
CANAL_RANGE_VERTICAL = 10   # How far vertically canals affect drops
CANAL_RANGE_HORIZONTAL = 30 # How far horizontally canals affect drops
CANAL_PULL_STRENGTH = 0.1 # How strongly canals pull drops

# Speed Settings
BOTTOM_SPEED_MULTIPLIER = 5.0  # How much faster drops move at bottom (multiplier)
SPEED_TRANSITION_HEIGHT = 0.3  # When drops start accelerating (0.5 = halfway)

# =============================================================================

class Canal:
    def __init__(self, x: float, y: float, strength: float = 0.1, initial_width: float = 2.0):
        self.x = x
        self.y = y
        self.strength = strength
        self.width = min(initial_width, CANAL_MAX_WIDTH)
        self.alpha = CANAL_ALPHA

    def update(self):
        self.strength = min(self.strength + CANAL_GROWTH_RATE, 1.0)
        self.width = min(CANAL_MAX_WIDTH, self.width + self.strength * CANAL_WIDTH_GROWTH)
        self.alpha = min(CANAL_ALPHA + int(self.strength * 95), 255)

    def draw(self, screen):
        canal_surface = pygame.Surface((int(self.width), 2), pygame.SRCALPHA)  # Thinner canals
        canal_surface.fill((150, 150, 255, self.alpha))
        screen.blit(canal_surface, (int(self.x - self.width/2), int(self.y)))

class Drop:
    def __init__(self, x: float, y: float, size: float = 2.0):
        self.x = x
        self.y = y
        self.size = size
        self.speed = 1 + size * DROP_SPEED_FACTOR
        self.velocity = self.speed
        self.alive = True
        # Surface tension properties
        self.stretch = 0.0
        self.wobble = 0.0
        self.wobble_direction = 1
        self.surface_energy = size * SURFACE_TENSION
        # Movement properties
        self.dx = 0  # Horizontal velocity
        self.movement_timer = random.random() * 6.28  # Random starting phase

    def update(self, height: int, canals: List[Canal]):
        # Update movement timer
        self.movement_timer += 0.05
        
        # Random sideways movement
        random_force = math.sin(self.movement_timer) * RANDOM_MOVEMENT
        wind = WIND_EFFECT * (1 + 0.2 * math.sin(self.movement_timer * 0.5))
        
        # Update horizontal velocity with momentum
        self.dx = self.dx * MOMENTUM_FACTOR + (random_force + wind) * 0.2
        self.x += self.dx
        
        # Base velocity
        if self.y > height * SPEED_TRANSITION_HEIGHT:
            progress = (self.y - height * SPEED_TRANSITION_HEIGHT) / (height * (1 - SPEED_TRANSITION_HEIGHT))
            target_velocity = self.speed * (1 + progress * BOTTOM_SPEED_MULTIPLIER)
        else:
            target_velocity = self.speed

        # Surface tension affects acceleration
        tension_factor = 1.0 - (self.stretch * SURFACE_TENSION)
        self.velocity += (target_velocity - self.velocity) * 0.1 * tension_factor
        
        # Update stretch based on total movement (vertical and horizontal)
        total_velocity = math.sqrt(self.velocity**2 + self.dx**2)
        target_stretch = (total_velocity / self.speed - 1) * (1 - TENSION_ROUNDNESS)
        self.stretch += (target_stretch - self.stretch) * 0.1
        
        # Limit stretch and check for breaking
        self.stretch = min(self.stretch, TENSION_BREAK_POINT)
        if self.stretch >= TENSION_BREAK_POINT and self.size > DROP_MIN_SIZE:
            self.break_drop()
            
        # Update wobble
        self.wobble += 0.1 * self.wobble_direction
        if abs(self.wobble) > TENSION_WOBBLE:
            self.wobble_direction *= -1
            
        self.y += self.velocity
        
        # Canal interaction with surface tension
        for canal in canals:
            if abs(self.y - canal.y) < CANAL_RANGE_VERTICAL:
                dx = canal.x - self.x
                dist = abs(dx)
                if dist < CANAL_RANGE_HORIZONTAL:
                    pull = (CANAL_RANGE_HORIZONTAL - dist) / CANAL_RANGE_HORIZONTAL * canal.strength
                    # Surface tension resists sudden movements
                    pull *= (1 - SURFACE_TENSION * 0.5)
                    self.x += dx * pull * CANAL_PULL_STRENGTH

        if self.y > height:
            self.alive = False

    def break_drop(self):
        # Drop breaks into two smaller drops due to stretching
        self.size *= 0.7
        self.stretch *= 0.5
        self.surface_energy = self.size * SURFACE_TENSION

    def draw(self, screen):
        # Calculate drop shape based on surface tension
        base_stretch = 1 + (self.stretch * DROP_STRETCH_FACTOR)
        wobble_effect = 1 + self.wobble
        
        # More rounded shape when surface tension is high
        roundness = TENSION_ROUNDNESS * (1 - self.stretch)
        width = int(self.size * (2 - self.stretch * (1 - roundness)))
        height = int(self.size * base_stretch * wobble_effect)
        
        # Draw main drop body
        pygame.draw.ellipse(screen, (150, 150, 255), 
                          (int(self.x - width/2), int(self.y - height/2),
                           width, height))
        
        # Add highlight to show surface tension
        if SURFACE_TENSION > 0.2:
            highlight_size = max(1, int(width * 0.3))
            pygame.draw.ellipse(screen, (200, 200, 255),
                              (int(self.x - width/4), int(self.y - height/4),
                               highlight_size, highlight_size))

    def check_collision(self, other: 'Drop') -> bool:
        # Surface tension affects collision range
        base_range = (self.size + other.size) * DROP_COLLISION_FACTOR
        # Drops are more likely to merge when surface tension is high
        tension_range = base_range * (1 + TENSION_MERGE_THRESHOLD * SURFACE_TENSION)
        
        distance = np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
        return distance < tension_range

class WaterDrops:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.drops: List[Drop] = []
        self.canals: List[Canal] = []
        self.spawn_timer = 0
        self.spawn_rate = DROP_SPAWN_RATE
        self.min_size = DROP_MIN_SIZE
        self.max_size = DROP_MAX_SIZE
        self.canal_grid = {}
        self.grid_size = CANAL_GRID_SIZE

    def spawn_drop(self):
        center_x = random.randint(0, self.width)
        num_drops = random.randint(*DROP_CLUSTER_SIZE)
        
        for _ in range(num_drops):
            x = center_x + random.gauss(0, DROP_CLUSTER_SPREAD)
            x = max(0, min(x, self.width))
            size = random.uniform(self.min_size, self.max_size)
            self.drops.append(Drop(x, 0, size))

    def add_canal(self, x: float, y: float, drop_size: float):
        grid_x = round(x / self.grid_size) * self.grid_size
        grid_y = round(y / self.grid_size) * self.grid_size
        key = (grid_x, grid_y)
        
        if key not in self.canal_grid:
            width = min(CANAL_MAX_WIDTH, drop_size)
            self.canal_grid[key] = Canal(grid_x, grid_y, strength=CANAL_STRENGTH_INCREASE, initial_width=width)
            self.canals.append(self.canal_grid[key])
        else:
            self.canal_grid[key].strength = min(1.0, self.canal_grid[key].strength + CANAL_STRENGTH_INCREASE)
            self.canal_grid[key].width = min(CANAL_MAX_WIDTH, self.canal_grid[key].width + CANAL_WIDTH_GROWTH)

    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:
            self.spawn_drop()
            self.spawn_timer = 0

        for canal in self.canals:
            canal.update()

        for drop in self.drops:
            old_pos = (drop.x, drop.y)
            drop.update(self.height, self.canals)
            
            if drop.velocity > 1:  # Create canals for moving drops
                self.add_canal(drop.x, drop.y, drop.size)

        # Merge colliding drops
        for i, drop1 in enumerate(self.drops):
            for j, drop2 in enumerate(self.drops[i+1:], i+1):
                if drop1.alive and drop2.alive and drop1.check_collision(drop2):
                    new_size = np.sqrt(drop1.size**2 + drop2.size**2)
                    new_x = (drop1.x * drop1.size + drop2.x * drop2.size) / (drop1.size + drop2.size)
                    new_y = (drop1.y * drop1.size + drop2.y * drop2.size) / (drop1.size + drop2.size)
                    new_drop = Drop(new_x, new_y, new_size)
                    new_drop.velocity = max(drop1.velocity, drop2.velocity)
                    drop1.alive = False
                    drop2.alive = False
                    self.drops.append(new_drop)

        self.drops = [drop for drop in self.drops if drop.alive]

    def draw(self, screen):
        for canal in self.canals:
            canal.draw(screen)
        for drop in self.drops:
            drop.draw(screen)

class ControlPanel:
    def __init__(self, manager: pygame_gui.UIManager, rect: pygame.Rect):
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=rect,
            manager=manager,
            starting_layer_height=1
        )
        
        # Calculate positions for sliders
        slider_width = rect.width - 20
        current_y = 10
        slider_height = 20
        gap = 30
        
        # Create sliders
        self.sliders = {}
        
        # Drop Settings
        self.add_slider("Drop Size", DROP_MIN_SIZE, 1, 10, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Drop Speed", DROP_SPEED_FACTOR, 0.01, 0.1, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Spawn Rate", DROP_SPAWN_RATE, 1, 30, current_y, slider_width, slider_height, manager)
        current_y += gap
        
        # Movement Settings
        current_y += 10  # Extra gap for section
        self.add_slider("Random Movement", RANDOM_MOVEMENT, 0, 2.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Momentum", MOMENTUM_FACTOR, 0, 1.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Wind Effect", WIND_EFFECT, -1.0, 1.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        
        # Surface Tension Settings
        current_y += 10  # Extra gap for section
        self.add_slider("Surface Tension", SURFACE_TENSION, 0, 1.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Drop Stretch", TENSION_BREAK_POINT, 0.5, 3.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        
        # Speed Settings
        current_y += 10  # Extra gap for section
        self.add_slider("Bottom Speed", BOTTOM_SPEED_MULTIPLIER, 1.0, 10.0, current_y, slider_width, slider_height, manager)
        current_y += gap
        self.add_slider("Speed Transition", SPEED_TRANSITION_HEIGHT, 0.1, 0.9, current_y, slider_width, slider_height, manager)

    def add_slider(self, name: str, default_value: float, min_value: float, max_value: float, 
                  y_pos: int, width: int, height: int, manager: pygame_gui.UIManager):
        # Create label
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, y_pos), (width, 15)),
            text=name,
            manager=manager,
            container=self.panel
        )
        
        # Create slider
        slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((10, y_pos + 15), (width, height)),
            start_value=default_value,
            value_range=(min_value, max_value),
            manager=manager,
            container=self.panel
        )
        self.sliders[name] = slider

    def get_values(self) -> dict:
        return {name: slider.get_current_value() for name, slider in self.sliders.items()}

def main():
    try:
        print("Initializing pygame...")
        pygame.init()
        
        print("Setting up display...")
        info = pygame.display.Info()
        width, height = info.current_w, info.current_h
        print(f"Screen dimensions: {width}x{height}")
        
        try:
            screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
        except pygame.error as e:
            print(f"Failed to set fullscreen mode: {e}")
            print("Trying windowed mode instead...")
            screen = pygame.display.set_mode((800, 600))
        
        # Initialize GUI
        manager = pygame_gui.UIManager((width, height))
        control_panel = ControlPanel(
            manager=manager,
            rect=pygame.Rect(width - 250, 0, 250, height)
        )
        
        clock = pygame.time.Clock()
        print("Display setup complete")

        simulation = WaterDrops(width - 250, height)  # Adjust width for control panel
        print("Simulation created")

        running = True
        while running:
            time_delta = clock.tick(60)/1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                
                # Handle GUI events
                manager.process_events(event)

            # Update GUI
            manager.update(time_delta)
            
            # Get values from sliders and update simulation parameters
            values = control_panel.get_values()
            global DROP_MIN_SIZE, DROP_SPEED_FACTOR, DROP_SPAWN_RATE
            global RANDOM_MOVEMENT, MOMENTUM_FACTOR, WIND_EFFECT
            global SURFACE_TENSION, TENSION_BREAK_POINT
            global BOTTOM_SPEED_MULTIPLIER, SPEED_TRANSITION_HEIGHT
            
            DROP_MIN_SIZE = values["Drop Size"]
            DROP_SPEED_FACTOR = values["Drop Speed"]
            DROP_SPAWN_RATE = int(values["Spawn Rate"])
            RANDOM_MOVEMENT = values["Random Movement"]
            MOMENTUM_FACTOR = values["Momentum"]
            WIND_EFFECT = values["Wind Effect"]
            SURFACE_TENSION = values["Surface Tension"]
            TENSION_BREAK_POINT = values["Drop Stretch"]
            BOTTOM_SPEED_MULTIPLIER = values["Bottom Speed"]
            SPEED_TRANSITION_HEIGHT = values["Speed Transition"]

            # Draw simulation
            screen.fill((0, 0, 0))
            simulation.update()
            simulation.draw(screen)
            
            # Draw GUI
            manager.draw_ui(screen)
            
            pygame.display.flip()

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main() 