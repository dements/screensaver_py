import pygame
import random
import math
import numpy as np

class Canal:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 1.0  # Starting width
        self.strength = 1.0  # How established the canal is
        self.decay_rate = 0.001  # How quickly the canal dries

    def update(self):
        self.strength *= (1 - self.decay_rate)
        return self.strength > 0.1  # Return False if canal is too weak

class Raindrop:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size  # Diameter in pixels
        self.speed = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.angle = 90  # Default downward direction in degrees
        
        # Physical properties from the paper
        self.mass = (math.pi * (size/2)**3) * 0.001  # Approximate mass (g)
        self.adhesion_force = size * 0.05  # Simplified adhesion force
        self.is_stuck = True
        self.in_canal = False
        self.canal_influence = 0.8  # How strongly canals affect drop movement
        
    def find_nearest_canal(self, canals, max_distance=20):
        nearest = None
        min_dist = max_distance
        
        for canal in canals:
            dist = math.sqrt((self.x - canal.x)**2 + (self.y - canal.y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = canal
                
        return nearest, min_dist

    def update(self, wind_speed, canals, gravity=9.81):
        if not self.is_stuck:
            # Find nearby canal
            nearest_canal, distance = self.find_nearest_canal(canals)
            
            if nearest_canal and distance < 20:
                # Follow canal with some randomness
                canal_direction = math.atan2(1, 0)  # Straight down
                self.velocity_x = (1 - self.canal_influence) * self.velocity_x + \
                                self.canal_influence * (math.cos(canal_direction) * 2)
                self.velocity_y = (1 - self.canal_influence) * self.velocity_y + \
                                self.canal_influence * (math.sin(canal_direction) * 2)
                
                # Strengthen the canal
                nearest_canal.strength += 0.1
                nearest_canal.width = min(nearest_canal.width + 0.01, 3.0)
                self.in_canal = True
            else:
                # Normal physics as before
                gravity_force = self.mass * gravity * 2
                wind_force = 0.5 * 1.225 * (self.size/1000)**2 * wind_speed**2
                
                self.velocity_x += wind_force * 0.1
                self.velocity_y += gravity_force * 0.1
                self.in_canal = False
            
            self.x += self.velocity_x
            self.y += self.velocity_y
            self.angle = math.degrees(math.atan2(self.velocity_y, self.velocity_x))
            
        else:
            total_force = math.sqrt((wind_speed**2 + gravity**2))
            if total_force > self.adhesion_force * 0.5:
                self.is_stuck = False

class Screensaver:
    def __init__(self, width=800, height=600):
        pygame.init()
        # Get the screen info for fullscreen
        screen_info = pygame.display.Info()
        self.width = screen_info.current_w
        self.height = screen_info.current_h
        # Set fullscreen mode
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption("Raindrop Screensaver")
        
        self.drops = []
        self.wind_speed = 3.0  # Increased base wind speed
        self.running = True
        
        # Initialize more drops for larger screen
        for _ in range(100):  # Increased number of drops
            self.add_drop()

        self.canals = []
        self.canal_grid_size = 20  # Space between potential canal positions
        self.setup_canal_grid()

    def setup_canal_grid(self):
        # Create a grid of potential canal positions
        for x in range(0, self.width, self.canal_grid_size):
            for y in range(0, self.height, self.canal_grid_size):
                if random.random() < 0.1:  # 10% chance of canal at each position
                    self.canals.append(Canal(x, y))

    def add_drop(self):
        x = random.randint(0, self.width)
        y = random.randint(0, self.height)
        size = random.uniform(2, 8)
        self.drops.append(Raindrop(x, y, size))

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Update wind speed with some variation
            self.wind_speed = 3.0 + math.sin(pygame.time.get_ticks() * 0.001) * 1.0

            # Update and draw drops
            self.screen.fill((0, 0, 0))  # Clear screen
            
            # Update and draw canals
            self.canals = [canal for canal in self.canals if canal.update()]
            for canal in self.canals:
                # Ensure alpha and color values are valid integers in range [0, 255]
                alpha = max(0, min(255, int(canal.strength * 128)))
                canal_color = (0, 50, 100, alpha)  # RGBA color tuple
                
                # Create surface for the canal
                surf = pygame.Surface((int(canal.width * 2), int(canal.width * 2)), pygame.SRCALPHA)
                pygame.draw.circle(surf, canal_color,
                                 (int(canal.width), int(canal.width)),
                                 max(1, int(canal.width)))
                self.screen.blit(surf, (int(canal.x - canal.width), int(canal.y - canal.width)))
            
            # Update and draw drops
            for drop in self.drops:
                drop.update(self.wind_speed, self.canals)
                
                # Draw drop with different color if in canal
                color = (50, 100, 255) if drop.in_canal else (100, 150, 255)
                pygame.draw.circle(self.screen, color,
                                 (int(drop.x), int(drop.y)),
                                 int(drop.size/2))
                
                # Create new canal where drops fall
                if random.random() < 0.01:  # 1% chance per drop per frame
                    self.canals.append(Canal(drop.x, drop.y))
                
                # Remove drops that go off screen and add new ones
                if drop.y > self.height or drop.x > self.width or drop.x < 0:
                    self.drops.remove(drop)
                    self.add_drop()

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

if __name__ == "__main__":
    screensaver = Screensaver()
    screensaver.run() 