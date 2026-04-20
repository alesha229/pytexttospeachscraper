# Expression Controls

## Overview

Expression controls are effects that provide user-controllable parameters for expressions. They allow scripts and users to create interactive controls for animations without manually editing expression code.

## Expression Control Types

### Available Control Types

```javascript
// Slider Control - Numeric value
var slider = layer.property("Effects").addProperty("ADBE Slider Control");

// Angle Control - Angle value
var angle = layer.property("Effects").addProperty("ADBE Angle Control");

// Checkbox Control - Boolean value
var checkbox = layer.property("Effects").addProperty("ADBE Checkbox Control");

// Color Control - Color value
var color = layer.property("Effects").addProperty("ADBE Color Control");

// Point Control - 2D point
var point = layer.property("Effects").addProperty("ADBE Point Control");

// Layer Control - Layer reference
var layerControl = layer.property("Effects").addProperty("ADBE Layer Control");

// Dropdown Menu Control - Menu selection
var dropdown = layer.property("Effects").addProperty("ADBE Dropdown Control");
```

## Slider Control

### Creating Slider Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add slider control
var slider = effects.addProperty("ADBE Slider Control");
slider.name = "My Slider";

// Access slider value property
var sliderValue = slider.property("Slider");

// Set slider value
sliderValue.setValue(50);

// Set range (via expression or manual limits)
// Note: Slider has no built-in min/max, use expressions to clamp
```

### Using Slider in Expressions

```javascript
var layer = comp.layers.addNull();
var slider = layer.property("Effects").addProperty("ADBE Slider Control");
slider.name = "Speed";
slider.property("Slider").setValue(100);

// Use slider in another layer's expression
var targetLayer = comp.layers.addSolid([1, 0, 0], "Target", 100, 100, 1.0);
var position = targetLayer.property("Position");

// Reference slider
position.expression = "[time * effect('Speed')('Slider'), 540]";

// Or use match name
position.expression = "[time * effect('Speed')('ADBE Slider Control')('Slider'), 540]";
```

### Multiple Sliders

```javascript
var controller = comp.layers.addNull();
controller.name = "Controller";

var effects = controller.property("Effects");

// Add multiple sliders
var widthSlider = effects.addProperty("ADBE Slider Control");
widthSlider.name = "Width";
widthSlider.property("Slider").setValue(200);

var heightSlider = effects.addProperty("ADBE Slider Control");
heightSlider.name = "Height";
heightSlider.property("Slider").setValue(100);

var countSlider = effects.addProperty("ADBE Slider Control");
countSlider.name = "Count";
countSlider.property("Slider").setValue(5);

// Use in expression
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");
var rect = groupContents.addProperty("ADBE Vector Shape - Rect");

var size = rect.property("ADBE Vector Rect Size");
size.expression = "[thisComp.layer('Controller').effect('Width')('Slider'), thisComp.layer('Controller').effect('Height')('Slider')]";
```

## Angle Control

### Creating Angle Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add angle control
var angle = effects.addProperty("ADBE Angle Control");
angle.name = "Rotation Angle";

// Access angle value property
var angleValue = angle.property("Angle");

// Set angle value (in degrees)
angleValue.setValue(45);
```

### Using Angle in Expressions

```javascript
var controller = comp.layers.addNull();
var angle = controller.property("Effects").addProperty("ADBE Angle Control");
angle.name = "Angle";
angle.property("Angle").setValue(90);

// Use angle in rotation
var layer = comp.layers.addSolid([1, 0, 0], "Rotating", 100, 100, 1.0);
var rotation = layer.property("Rotation");

rotation.expression = "thisComp.layer('Controller').effect('Angle')('Angle')";
```

## Checkbox Control

### Creating Checkbox Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add checkbox control
var checkbox = effects.addProperty("ADBE Checkbox Control");
checkbox.name = "Enable Effect";

// Access checkbox value property
var checkboxValue = checkbox.property("Checkbox");

// Set checkbox value (0 = off, 1 = on)
checkboxValue.setValue(0);  // Unchecked
checkboxValue.setValue(1);  // Checked
```

### Using Checkbox in Expressions

```javascript
var controller = comp.layers.addNull();
var checkbox = controller.property("Effects").addProperty("ADBE Checkbox Control");
checkbox.name = "Show";
checkbox.property("Checkbox").setValue(1);

// Use checkbox to toggle visibility
var layer = comp.layers.addSolid([1, 0, 0], "Toggle", 100, 100, 1.0);
var opacity = layer.property("Opacity");

opacity.expression = "thisComp.layer('Controller').effect('Show')('Checkbox') * 100";

// Conditional expression
var position = layer.property("Position");
position.expression = "if (thisComp.layer('Controller').effect('Show')('Checkbox') == 1) [960, 540] else [-100, 540]";
```

## Color Control

### Creating Color Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add color control
var colorControl = effects.addProperty("ADBE Color Control");
colorControl.name = "Main Color";

// Access color value property
var colorValue = colorControl.property("Color");

// Set color value [R, G, B] 0.0-1.0
colorValue.setValue([1, 0, 0]);  // Red
colorValue.setValue([0, 1, 0]);  // Green
colorValue.setValue([0, 0, 1]);  // Blue
```

### Using Color in Expressions

```javascript
var controller = comp.layers.addNull();
var colorControl = controller.property("Effects").addProperty("ADBE Color Control");
colorControl.name = "Fill Color";
colorControl.property("Color").setValue([1, 0.5, 0]);

// Use color in shape layer
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");
var rect = groupContents.addProperty("ADBE Vector Shape - Rect");
rect.property("ADBE Vector Rect Size").setValue([200, 100]);

var fill = groupContents.addProperty("ADBE Vector Graphic - Fill");
var fillColor = fill.property("ADBE Vector Fill Color");

fillColor.expression = "thisComp.layer('Controller').effect('Fill Color')('Color')";
```

## Point Control

### Creating Point Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add point control
var point = effects.addProperty("ADBE Point Control");
point.name = "Target Point";

// Access point value property
var pointValue = point.property("Point");

// Set point value [x, y]
pointValue.setValue([960, 540]);
```

### Using Point in Expressions

```javascript
var controller = comp.layers.addNull();
var point = controller.property("Effects").addProperty("ADBE Point Control");
point.name = "Position";
point.property("Point").setValue([960, 540]);

// Use point for position
var layer = comp.layers.addSolid([1, 0, 0], "Target", 100, 100, 1.0);
var position = layer.property("Position");

position.expression = "thisComp.layer('Controller').effect('Position')('Point')";

// Offset from point
position.expression = "thisComp.layer('Controller').effect('Position')('Point') + [50, 0]";
```

## Layer Control

### Creating Layer Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add layer control
var layerControl = effects.addProperty("ADBE Layer Control");
layerControl.name = "Target Layer";

// Access layer value property
var layerValue = layerControl.property("Layer");

// Set layer value (by layer index)
layerValue.setValue(1);  // Reference to layer 1
```

### Using Layer Control in Expressions

```javascript
var controller = comp.layers.addNull();
var layerControl = controller.property("Effects").addProperty("ADBE Layer Control");
layerControl.name = "Source";
layerControl.property("Layer").setValue(1);

// Use layer control to reference another layer
var position = controller.property("Position");
position.expression = "thisComp.layer('Controller').effect('Source')('Layer').transform.position";

// Get position from controlled layer
var targetLayer = comp.layer(1);
var follower = comp.layers.addSolid([1, 0, 0], "Follower", 50, 50, 1.0);
var followerPos = follower.property("Position");

followerPos.expression = "thisComp.layer('Controller').effect('Source')('Layer').transform.position + [100, 0]";
```

## Dropdown Menu Control

### Creating Dropdown Controls

```javascript
var layer = comp.layers.addNull();
var effects = layer.property("Effects");

// Add dropdown control
var dropdown = effects.addProperty("ADBE Dropdown Control");
dropdown.name = "Mode";

// Access dropdown value property
var dropdownValue = dropdown.property("Menu");

// Set dropdown value (index, 1-based)
dropdownValue.setValue(1);  // First option

// Note: Dropdown options are set via the effect's menu items
// and cannot be dynamically populated via script
```

### Using Dropdown in Expressions

```javascript
var controller = comp.layers.addNull();
var dropdown = controller.property("Effects").addProperty("ADBE Dropdown Control");
dropdown.name = "Animation Type";

// Use dropdown in expression
var layer = comp.layers.addSolid([1, 0, 0], "Animated", 100, 100, 1.0);
var position = layer.property("Position");

position.expression = `
var mode = thisComp.layer('Controller').effect('Animation Type')('Menu');
if (mode == 1) {
    [time * 100, 540];  // Slide right
} else if (mode == 2) {
    [960, time * 100];  // Fall down
} else {
    [960 + Math.sin(time) * 200, 540];  // Oscillate
}
`;
```

## Expression Syntax

### Referencing Controls

```javascript
// By name
var value = effect("My Slider")("Slider");

// By match name
var value = effect("My Slider")("ADBE Slider Control")("Slider");

// From another layer
var value = thisComp.layer("Controller").effect("My Slider")("Slider");

// Using variable
var controller = thisComp.layer("Controller");
var sliderValue = controller.effect("Speed")("Slider");
```

### Common Expression Patterns

```javascript
// Link to slider
var speed = effect("Speed")("Slider");
position = [time * speed, 540];

// Clamp slider value
var value = effect("Slider")("Slider");
var clamped = clamp(value, 0, 100);

// Conditional based on checkbox
var show = effect("Show")("Checkbox");
opacity = show ? 100 : 0;

// Switch based on dropdown
var mode = effect("Mode")("Menu");
result = mode == 1 ? "Option 1" : "Option 2";

// Color from control
fillColor = effect("Color")("Color");

// Point for position
target = effect("Target")("Point");
position = target;

// Angle for rotation
angle = effect("Angle")("Angle");
rotation = angle;
```

## Expression Control Utilities

### Create Controller Rig

```javascript
function createControllerRig(comp, name) {
    var controller = comp.layers.addNull();
    controller.name = name || "Controller";
    
    var effects = controller.property("Effects");
    
    // Add common controls
    var speed = effects.addProperty("ADBE Slider Control");
    speed.name = "Speed";
    speed.property("Slider").setValue(100);
    
    var size = effects.addProperty("ADBE Slider Control");
    size.name = "Size";
    size.property("Slider").setValue(50);
    
    var opacity = effects.addProperty("ADBE Slider Control");
    opacity.name = "Opacity";
    opacity.property("Slider").setValue(100);
    
    var enable = effects.addProperty("ADBE Checkbox Control");
    enable.name = "Enable";
    enable.property("Checkbox").setValue(1);
    
    var color = effects.addProperty("ADBE Color Control");
    color.name = "Color";
    color.property("Color").setValue([1, 1, 1]);
    
    return controller;
}

// Usage
var controller = createControllerRig(comp, "Main Controller");
```

### Link Multiple Properties

```javascript
function linkToController(layer, controller, controlName, propertyName) {
    var prop = layer.property(propertyName);
    var control = controller.property("Effects").property(controlName);
    var controlProp = control.property(control.controlType);
    
    // Build expression
    var expr = "thisComp.layer('" + controller.name + "').effect('" + controlName + "')('" + controlProp.name + "')";
    
    // For opacity, multiply by 100
    if (propertyName === "Opacity") {
        expr += " * 100";
    }
    
    prop.expression = expr;
}

// Usage
var shapeLayer = comp.layers.addSolid([1, 0, 0], "Linked", 100, 100, 1.0);
linkToController(shapeLayer, controller, "Size", "Scale");
linkToController(shapeLayer, controller, "Opacity", "Opacity");
```

## Common Patterns

### Animated Slider

```javascript
var controller = comp.layers.addNull();
var slider = controller.property("Effects").addProperty("ADBE Slider Control");
slider.name = "Animated Value";

// Animate slider
var sliderValue = slider.property("Slider");
sliderValue.setValueAtTime(0, 0);
sliderValue.setValueAtTime(2, 100);

// Use in expression
var layer = comp.layers.addSolid([1, 0, 0], "Target", 100, 100, 1.0);
var position = layer.property("Position");
position.expression = "[thisComp.layer('Controller').effect('Animated Value')('Slider'), 540]";
```

### Toggle Animation

```javascript
var controller = comp.layers.addNull();
var checkbox = controller.property("Effects").addProperty("ADBE Checkbox Control");
checkbox.name = "Animate";

// Toggle keyframes
var checkboxValue = checkbox.property("Checkbox");
checkboxValue.setValueAtTime(0, 0);
checkboxValue.setValueAtTime(1, 1);
checkboxValue.setValueAtTime(2, 0);

// Use in expression
var layer = comp.layers.addSolid([1, 0, 0], "Toggle", 100, 100, 1.0);
var position = layer.property("Position");
position.expression = `
var animate = thisComp.layer('Controller').effect('Animate')('Checkbox');
if (animate == 1) {
    [time * 100, 540];
} else {
    [0, 540];
}
`;
```

### Color Theme

```javascript
var controller = comp.layers.addNull();

// Add color controls
var primaryColor = controller.property("Effects").addProperty("ADBE Color Control");
primaryColor.name = "Primary";
primaryColor.property("Color").setValue([1, 0, 0]);

var secondaryColor = controller.property("Effects").addProperty("ADBE Color Control");
secondaryColor.name = "Secondary";
secondaryColor.property("Color").setValue([0, 0, 1]);

// Apply to multiple layers
var layer1 = comp.layers.addSolid([1, 0, 0], "Primary Shape", 100, 100, 1.0);
var shapeContents1 = layer1.property("Contents").property("Rectangle 1").property("Contents");
var fill1 = shapeContents1.property("Fill 1");
fill1.property("ADBE Vector Fill Color").expression = "thisComp.layer('Controller').effect('Primary')('Color')";

var layer2 = comp.layers.addSolid([0, 0, 1], "Secondary Shape", 100, 100, 1.0);
var shapeContents2 = layer2.property("Contents").property("Rectangle 1").property("Contents");
var fill2 = shapeContents2.property("Fill 1");
fill2.property("ADBE Vector Fill Color").expression = "thisComp.layer('Controller').effect('Secondary')('Color')";
```

### Master Control

```javascript
var controller = comp.layers.addNull();

// Master scale
var masterScale = controller.property("Effects").addProperty("ADBE Slider Control");
masterScale.name = "Master Scale";
masterScale.property("Slider").setValue(100);

// Link multiple layers to master scale
for (var i = 1; i <= 5; i++) {
    var layer = comp.layers.addSolid([1, 1, 1], "Layer " + i, 100, 100, 1.0);
    var scale = layer.property("Scale");
    scale.expression = "var s = thisComp.layer('Controller').effect('Master Scale')('Slider'); [s, s]";
}
```

## Best Practices

1. **Name controls clearly** for easy identification
2. **Use null layers** as controllers
3. **Group related controls** on the same controller layer
4. **Use expressions** to link properties to controls
5. **Document control ranges** in comments or layer notes
6. **Use checkboxes** for boolean toggles
7. **Use sliders** for numeric values
8. **Use color controls** for color pickers
9. **Use point controls** for 2D positions
10. **Use layer controls** for layer references

## Notes

- Expression controls are effects on layers
- Controls are accessed via `effect()` in expressions
- Slider has no built-in min/max (use expressions to clamp)
- Checkbox values are 0 (off) or 1 (on)
- Color values are [R, G, B] 0.0-1.0
- Point values are [x, y] coordinates
- Layer values are layer indices
- Dropdown values are menu item indices
- Controls can be animated with keyframes
- Use null layers for organization
