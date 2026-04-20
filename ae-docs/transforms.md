# Transform Properties

## Overview

Transform properties control the position, scale, rotation, opacity, and anchor point of layers. These are the fundamental properties for animating and positioning layers in 2D and 3D space.

## Transform Group Structure

### Accessing Transform Properties

```javascript
var layer = comp.layer(1);

// Access transform group
var transform = layer.property("Transform");

// Access individual properties
var position = transform.property("Position");
var scale = transform.property("Scale");
var rotation = transform.property("Rotation");
var opacity = transform.property("Opacity");
var anchorPoint = transform.property("Anchor Point");

// Alternative: Direct access from layer
var position2 = layer.property("Position");
var scale2 = layer.property("Scale");
```

### 3D Transform Properties

```javascript
// Enable 3D layer
layer.threeDLayer = true;

// Access 3D properties
var xPosition = layer.property("X Position");
var yPosition = layer.property("Y Position");
var zPosition = layer.property("Z Position");
var orientation = layer.property("Orientation");
var xRotation = layer.property("X Rotation");
var yRotation = layer.property("Y Rotation");
var zRotation = layer.property("Z Rotation");

// Note: Rotation becomes Z Rotation when 3D is enabled
```

## Position

### 2D Position

```javascript
var position = layer.property("Position");

// Set position [x, y]
position.setValue([960, 540]);

// Get current position
var currentPos = position.value;  // Returns [x, y]
var x = currentPos[0];
var y = currentPos[1];

// Animate position
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(2, [1920, 540]);

// Set dimensions separately (if separated)
var xPos = layer.property("X Position");
var yPos = layer.property("Y Position");
xPos.setValue(960);
yPos.setValue(540);
```

### 3D Position

```javascript
layer.threeDLayer = true;
var position = layer.property("Position");

// Set 3D position [x, y, z]
position.setValue([960, 540, 100]);

// Access individual axes
var xPos = layer.property("X Position");
var yPos = layer.property("Y Position");
var zPos = layer.property("Z Position");

xPos.setValue(960);
yPos.setValue(540);
zPos.setValue(100);

// Animate in 3D space
position.setValueAtTime(0, [0, 540, 0]);
position.setValueAtTime(1, [960, 540, 500]);
position.setValueAtTime(2, [1920, 540, 0]);
```

### Position Expressions

```javascript
var position = layer.property("Position");

// Follow another layer
position.expression = "thisComp.layer('Leader').transform.position";

// Offset from another layer
position.expression = "thisComp.layer('Leader').transform.position + [100, 0]";

// Wiggle
position.expression = "wiggle(2, 50)";

// Circular motion
position.expression = "[960 + Math.cos(time) * 200, 540 + Math.sin(time) * 200]";

// Bounce
position.expression = "[960, 540 + Math.abs(Math.sin(time * 3)) * -200]";
```

## Scale

### Uniform Scale

```javascript
var scale = layer.property("Scale");

// Set uniform scale [x, y]
scale.setValue([100, 100]);  // 100% = original size

// Scale up
scale.setValue([150, 150]);  // 150%

// Scale down
scale.setValue([50, 50]);    // 50%

// Animate scale
scale.setValueAtTime(0, [0, 0]);
scale.setValueAtTime(0.5, [120, 120]);
scale.setValueAtTime(1, [100, 100]);
```

### Non-Uniform Scale

```javascript
var scale = layer.property("Scale");

// Stretch horizontally
scale.setValue([200, 100]);

// Stretch vertically
scale.setValue([100, 200]);

// Flip horizontally
scale.setValue([-100, 100]);

// Flip vertically
scale.setValue([100, -100]);

// Animate non-uniform
scale.setValueAtTime(0, [100, 100]);
scale.setValueAtTime(0.5, [200, 50]);
scale.setValueAtTime(1, [100, 100]);
```

### 3D Scale

```javascript
layer.threeDLayer = true;
var scale = layer.property("Scale");

// Set 3D scale [x, y, z]
scale.setValue([100, 100, 100]);

// Scale in Z dimension
scale.setValue([100, 100, 200]);  // Stretch in Z
```

### Scale Expressions

```javascript
var scale = layer.property("Scale");

// Pulse
scale.expression = "[100 + Math.sin(time * 3) * 20, 100 + Math.sin(time * 3) * 20]";

// Scale based on audio amplitude
scale.expression = "var amp = thisComp.layer('Audio').effect('Both Channels')('Slider'); [100 + amp, 100 + amp]";

// Maintain aspect ratio
scale.expression = "var s = value[0]; [s, s]";
```

## Rotation

### 2D Rotation

```javascript
var rotation = layer.property("Rotation");

// Set rotation in degrees
rotation.setValue(0);      // No rotation
rotation.setValue(45);     // 45 degrees clockwise
rotation.setValue(90);     // 90 degrees
rotation.setValue(180);    // Half turn
rotation.setValue(360);    // Full turn

// Negative rotation
rotation.setValue(-45);    // 45 degrees counter-clockwise

// Animate rotation
rotation.setValueAtTime(0, 0);
rotation.setValueAtTime(2, 360);  // One full rotation

// Multiple rotations
rotation.setValue(720);    // Two full rotations
```

### 3D Rotation

```javascript
layer.threeDLayer = true;

// Access 3D rotation properties
var xRotation = layer.property("X Rotation");
var yRotation = layer.property("Y Rotation");
var zRotation = layer.property("Z Rotation");

// Or use orientation for 3D rotation
var orientation = layer.property("Orientation");

// Set rotation around each axis
xRotation.setValue(45);    // Pitch
yRotation.setValue(45);    // Yaw
zRotation.setValue(45);    // Roll

// Set orientation [x, y, z]
orientation.setValue([45, 45, 45]);

// Animate 3D rotation
xRotation.setValueAtTime(0, 0);
xRotation.setValueAtTime(2, 360);

yRotation.setValueAtTime(0, 0);
yRotation.setValueAtTime(2, 360);
```

### Rotation Expressions

```javascript
var rotation = layer.property("Rotation");

// Constant rotation
rotation.expression = "time * 90";  // 90 degrees per second

// Oscillating rotation
rotation.expression = "Math.sin(time * 2) * 30";  // +/- 30 degrees

// Random rotation
rotation.expression = "Math.random() * 360";

// Follow another layer's rotation
rotation.expression = "thisComp.layer('Leader').transform.rotation";

// Ping-pong rotation
rotation.expression = "loopOut('pingpong')";
```

## Opacity

### Basic Opacity

```javascript
var opacity = layer.property("Opacity");

// Set opacity (0-100)
opacity.setValue(100);   // Fully opaque
opacity.setValue(50);    // 50% transparent
opacity.setValue(0);     // Fully transparent

// Fade in
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(1, 100);

// Fade out
opacity.setValueAtTime(2, 100);
opacity.setValueAtTime(3, 0);

// Fade in and out
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(0.5, 100);
opacity.setValueAtTime(2, 100);
opacity.setValueAtTime(2.5, 0);
```

### Opacity Expressions

```javascript
var opacity = layer.property("Opacity");

// Blinking
opacity.expression = "Math.sin(time * 5) > 0 ? 100 : 0";

// Fade based on distance
opacity.expression = "var d = length(position, thisComp.layer('Target').transform.position); linear(d, 0, 500, 100, 0)";

// Random flicker
opacity.expression = "Math.random() * 50 + 50";  // 50-100%

// Audio reactive
opacity.expression = "thisComp.layer('Audio').effect('Both Channels')('Slider')";
```

## Anchor Point

### 2D Anchor Point

```javascript
var anchorPoint = layer.property("Anchor Point");

// Set anchor point (relative to layer)
anchorPoint.setValue([0, 0]);          // Top-left corner
anchorPoint.setValue([960, 540]);      // Center (for 1920x1080)
anchorPoint.setValue([1920, 1080]);    // Bottom-right corner

// Center anchor point
anchorPoint.setValue([layer.width / 2, layer.height / 2]);

// Animate anchor point
anchorPoint.setValueAtTime(0, [0, 0]);
anchorPoint.setValueAtTime(1, [layer.width, layer.height]);
```

### 3D Anchor Point

```javascript
layer.threeDLayer = true;
var anchorPoint = layer.property("Anchor Point");

// Set 3D anchor point [x, y, z]
anchorPoint.setValue([layer.width / 2, layer.height / 2, 0]);
```

### Anchor Point Expressions

```javascript
var anchorPoint = layer.property("Anchor Point");

// Follow position
anchorPoint.expression = "transform.position";

// Center of layer
anchorPoint.expression = "[width / 2, height / 2]";
```

## Transform Animation

### Position and Scale Animation

```javascript
var position = layer.property("Position");
var scale = layer.property("Scale");

// Zoom in from center
scale.setValueAtTime(0, [0, 0]);
scale.setValueAtTime(1, [100, 100]);

// Slide in from left
position.setValueAtTime(0, [-200, 540]);
position.setValueAtTime(0.5, [960, 540]);
```

### Rotation and Opacity Animation

```javascript
var rotation = layer.property("Rotation");
var opacity = layer.property("Opacity");

// Spin and fade in
rotation.setValueAtTime(0, -180);
rotation.setValueAtTime(1, 0);
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(1, 100);
```

### 3D Transform Animation

```javascript
layer.threeDLayer = true;

var position = layer.property("Position");
var orientation = layer.property("Orientation");
var scale = layer.property("Scale");

// Fly in from back
position.setValueAtTime(0, [960, 540, -1000]);
position.setValueAtTime(2, [960, 540, 0]);

// Rotate while flying
orientation.setValueAtTime(0, [0, 180, 0]);
orientation.setValueAtTime(2, [0, 0, 0]);

// Scale up
scale.setValueAtTime(0, [0, 0, 0]);
scale.setValueAtTime(2, [100, 100, 100]);
```

## Transform Interpolation

### Setting Keyframe Interpolation

```javascript
var position = layer.property("Position");

// Set keyframes
position.setValueAtTime(0, [0, 540]);
position.setValueAtTime(2, [1920, 540]);

// Set temporal interpolation
position.setTemporalInterpolationAtKey(1, KeyframeInterpolationType.BEZIER);
position.setTemporalInterpolationAtKey(2, KeyframeInterpolationType.BEZIER);

// Set spatial interpolation
position.setSpatialInterpolationAtKey(1, KeyframeSpatialInterpolationType.BEZIER);
position.setSpatialInterpolationAtKey(2, KeyframeSpatialInterpolationType.BEZIER);

// Set ease
var easeIn = new KeyframeEase(0.33, 50);
var easeOut = new KeyframeEase(0.33, 50);
position.setTemporalEaseAtKey(1, [easeIn], [easeOut]);
position.setTemporalEaseAtKey(2, [easeIn], [easeOut]);
```

### Hold Keyframes

```javascript
var opacity = layer.property("Opacity");

// Create stepped animation
opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(1, 100);
opacity.setValueAtTime(2, 0);
opacity.setValueAtTime(3, 100);

// Set hold interpolation
for (var i = 1; i <= opacity.numKeys; i++) {
    opacity.setTemporalInterpolationAtKey(i, KeyframeInterpolationType.HOLD);
}
```

## Transform Expressions

### Linking Transforms

```javascript
// Link position to another layer
position.expression = "thisComp.layer('Leader').transform.position";

// Link scale to another layer's scale
scale.expression = "thisComp.layer('Leader').transform.scale";

// Link rotation to another layer's rotation
rotation.expression = "thisComp.layer('Leader').transform.rotation";

// Link opacity to another layer's opacity
opacity.expression = "thisComp.layer('Leader').transform.opacity";
```

### Mathematical Transforms

```javascript
// Circular motion
position.expression = "[960 + Math.cos(time) * 200, 540 + Math.sin(time) * 200]";

// Spiral motion
position.expression = "[960 + Math.cos(time) * time * 50, 540 + Math.sin(time) * time * 50]";

// Oscillating scale
scale.expression = "[100 + Math.sin(time * 2) * 20, 100 + Math.sin(time * 2) * 20]";

// Pendulum rotation
rotation.expression = "Math.sin(time * 2) * 30";
```

### Conditional Transforms

```javascript
// Scale based on position
scale.expression = "position[0] > 960 ? [150, 150] : [100, 100]";

// Opacity based on time
opacity.expression = "time > 2 ? 100 : 0";

// Rotation based on layer index
rotation.expression = "index * 30";
```

## Transform Utilities

### Center Layer

```javascript
function centerLayer(layer) {
    var comp = layer.containingComp;
    var position = layer.property("Position");
    var anchorPoint = layer.property("Anchor Point");
    
    // Set anchor point to center of layer
    anchorPoint.setValue([layer.width / 2, layer.height / 2]);
    
    // Set position to center of comp
    position.setValue([comp.width / 2, comp.height / 2]);
}

// Usage
centerLayer(comp.layer(1));
```

### Align Layers

```javascript
function alignLayers(layers, alignment) {
    // alignment: 'left', 'center', 'right', 'top', 'middle', 'bottom'
    var firstLayer = layers[0];
    var firstPos = firstLayer.property("Position").value;
    var firstAnchor = firstLayer.property("Anchor Point").value;
    
    for (var i = 1; i < layers.length; i++) {
        var layer = layers[i];
        var pos = layer.property("Position");
        var anchor = layer.property("Anchor Point");
        
        var newPos = firstPos;
        
        if (alignment === 'left') {
            newPos[0] = firstPos[0] - firstAnchor[0] + anchor[0];
        } else if (alignment === 'center') {
            // Already centered on first layer
        } else if (alignment === 'right') {
            newPos[0] = firstPos[0] + (firstLayer.width - firstAnchor[0]) - (layer.width - anchor[0]);
        } else if (alignment === 'top') {
            newPos[1] = firstPos[1] - firstAnchor[1] + anchor[1];
        } else if (alignment === 'bottom') {
            newPos[1] = firstPos[1] + (firstLayer.height - firstAnchor[1]) - (layer.height - anchor[1]);
        }
        
        pos.setValue(newPos);
    }
}

// Usage
var layers = [comp.layer(1), comp.layer(2), comp.layer(3)];
alignLayers(layers, 'center');
```

### Create Circular Arrangement

```javascript
function arrangeInCircle(layers, radius, center) {
    center = center || [960, 540];
    
    for (var i = 0; i < layers.length; i++) {
        var angle = (i / layers.length) * Math.PI * 2;
        var x = center[0] + Math.cos(angle) * radius;
        var y = center[1] + Math.sin(angle) * radius;
        
        layers[i].property("Position").setValue([x, y]);
        
        // Point toward center
        var rotation = layers[i].property("Rotation");
        rotation.setValue((angle * 180 / Math.PI) + 90);
    }
}

// Usage
var layers = [];
for (var i = 0; i < 8; i++) {
    layers.push(comp.layers.addSolid([1, 1, 1], "Dot", 50, 50, 1.0));
}
arrangeInCircle(layers, 200, [960, 540]);
```

## Common Patterns

### Zoom In Effect

```javascript
var scale = layer.property("Scale");
var position = layer.property("Position");

scale.setValueAtTime(0, [50, 50]);
scale.setValueAtTime(1, [100, 100]);

position.setValueAtTime(0, [960, 540]);
position.setValueAtTime(1, [960, 540]);
```

### Slide In Effect

```javascript
var position = layer.property("Position");
var opacity = layer.property("Opacity");

position.setValueAtTime(0, [-200, 540]);
position.setValueAtTime(0.5, [960, 540]);

opacity.setValueAtTime(0, 0);
opacity.setValueAtTime(0.25, 100);
```

### Bounce Effect

```javascript
var position = layer.property("Position");

position.setValueAtTime(0, [960, 0]);
position.setValueAtTime(0.3, [960, 540]);
position.setValueAtTime(0.45, [960, 490]);
position.setValueAtTime(0.6, [960, 540]);
position.setValueAtTime(0.7, [960, 520]);
position.setValueAtTime(0.8, [960, 540]);
```

### Pulsing Effect

```javascript
var scale = layer.property("Scale");
var opacity = layer.property("Opacity");

scale.setValueAtTime(0, [100, 100]);
scale.setValueAtTime(0.5, [120, 120]);
scale.setValueAtTime(1, [100, 100]);

opacity.setValueAtTime(0, 100);
opacity.setValueAtTime(0.5, 70);
opacity.setValueAtTime(1, 100);
```

### 3D Flip

```javascript
layer.threeDLayer = true;

var orientation = layer.property("Orientation");
var scale = layer.property("Scale");

orientation.setValueAtTime(0, [0, 0, 0]);
orientation.setValueAtTime(1, [0, 180, 0]);

scale.setValueAtTime(0.5, [0, 100, 100]);  // Narrow at midpoint
scale.setValueAtTime(1, [100, 100, 100]);
```

## Best Practices

1. **Use anchor point** to control transformation center
2. **Enable 3D layer** before accessing 3D transform properties
3. **Use expressions** for procedural animation
4. **Set interpolation** for smooth animations
5. **Use hold keyframes** for stepped animations
6. **Link transforms** using expressions for consistency
7. **Consider performance** when using complex expressions
8. **Use separate dimensions** for independent axis animation
9. **Name keyframes** or use markers for timing reference
10. **Test animations** at different frame rates

## Notes

- Position values are in composition coordinates
- Scale values are percentages (100 = original size)
- Rotation values are in degrees
- Opacity values are 0-100
- Anchor point is relative to layer
- 3D transforms require `threeDLayer = true`
- Rotation becomes Z Rotation in 3D
- Use `setParentWithJump()` to avoid transform changes when parenting
- Transform properties can be separated for independent axis control
- Expressions can link transforms between layers
