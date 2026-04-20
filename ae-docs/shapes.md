# Shape Layers

## Overview

Shape layers are vector-based layers that contain shape groups with paths, fills, strokes, and modifiers. They provide powerful tools for creating procedural graphics, animations, and motion design elements.

## Shape Layer Creation

### Creating Shape Layers

```javascript
var comp = app.project.activeItem;

// Create empty shape layer
var shapeLayer = comp.layers.addShape();
shapeLayer.name = "My Shape Layer";

// Shape layers start with a Transform group and Contents group
var contents = shapeLayer.property("Contents");
var transform = shapeLayer.property("Transform");
```

### Adding Shapes to Layer

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add rectangle group
var rectGroup = contents.addProperty("ADBE Vector Group");
rectGroup.name = "Rectangle 1";

// Add ellipse group
var ellipseGroup = contents.addProperty("ADBE Vector Group");
ellipseGroup.name = "Ellipse 1";

// Add polygon group
var polygonGroup = contents.addProperty("ADBE Vector Group");
polygonGroup.name = "Polygon 1";

// Add star group
var starGroup = contents.addProperty("ADBE Vector Group");
starGroup.name = "Star 1";
```

## Shape Objects

### Shape Property Structure

Each shape group (ADBE Vector Group) contains:
- **Contents** (ADBE Vectors Group) - Contains shapes and modifiers
- **Transform** (ADBE Vector Transform Group) - Shape-specific transform

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add shape group
var group = contents.addProperty("ADBE Vector Group");
group.name = "My Shape";

// Access group contents
var groupContents = group.property("ADBE Vectors Group");

// Access group transform
var groupTransform = group.property("ADBE Vector Transform Group");
var groupPosition = groupTransform.property("ADBE Vector Position");
var groupScale = groupTransform.property("ADBE Vector Scale");
var groupRotation = groupTransform.property("ADBE Vector Rotation");
var groupOpacity = groupTransform.property("ADBE Vector Opacity");
```

## Shape Types

### Rectangle

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add rectangle group
var rectGroup = contents.addProperty("ADBE Vector Group");
var rectContents = rectGroup.property("ADBE Vectors Group");

// Add rectangle path
var rectPath = rectContents.addProperty("ADBE Vector Shape - Rect");
rectPath.name = "Rect Path";

// Set rectangle properties
var size = rectPath.property("ADBE Vector Rect Size");
size.setValue([200, 100]);  // [width, height]

var position = rectPath.property("ADBE Vector Rect Position");
position.setValue([0, 0]);

var roundness = rectPath.property("ADBE Vector Rect Roundness");
roundness.setValue(10);

// Add fill
var fill = rectContents.addProperty("ADBE Vector Graphic - Fill");
fill.name = "Fill";
var fillColor = fill.property("ADBE Vector Fill Color");
fillColor.setValue([1, 0, 0, 1]);  // [R, G, B, A]

// Add stroke
var stroke = rectContents.addProperty("ADBE Vector Graphic - Stroke");
stroke.name = "Stroke";
var strokeColor = stroke.property("ADBE Vector Stroke Color");
strokeColor.setValue([0, 0, 0, 1]);
var strokeWidth = stroke.property("ADBE Vector Stroke Width");
strokeWidth.setValue(2);
```

### Ellipse

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add ellipse group
var ellipseGroup = contents.addProperty("ADBE Vector Group");
var ellipseContents = ellipseGroup.property("ADBE Vectors Group");

// Add ellipse path
var ellipsePath = ellipseContents.addProperty("ADBE Vector Shape - Ellipse");
ellipsePath.name = "Ellipse Path";

// Set ellipse properties
var ellipseSize = ellipsePath.property("ADBE Vector Ellipse Size");
ellipseSize.setValue([150, 150]);  // [width, height]

var ellipsePosition = ellipsePath.property("ADBE Vector Ellipse Position");
ellipsePosition.setValue([0, 0]);

// Add fill
var fill = ellipseContents.addProperty("ADBE Vector Graphic - Fill");
var fillColor = fill.property("ADBE Vector Fill Color");
fillColor.setValue([0, 1, 0, 1]);  // Green
```

### Polygon

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add polygon group
var polygonGroup = contents.addProperty("ADBE Vector Group");
var polygonContents = polygonGroup.property("ADBE Vectors Group");

// Add polygon path
var polygonPath = polygonContents.addProperty("ADBE Vector Shape - Star");
polygonPath.name = "Polygon";

// Configure as polygon
var points = polygonPath.property("ADBE Vector Star Points");
points.setValue(5);  // Number of sides/points

var innerRadius = polygonPath.property("ADBE Vector Star Inner Radius");
innerRadius.setValue(0);  // 0 for polygon, >0 for star

var outerRadius = polygonPath.property("ADBE Vector Star Outer Radius");
outerRadius.setValue(75);

var rotation = polygonPath.property("ADBE Vector Star Rotation");
rotation.setValue(0);

var roundness = polygonPath.property("ADBE Vector Star Roundness");
roundness.setValue(0);

// Add fill
var fill = polygonContents.addProperty("ADBE Vector Graphic - Fill");
var fillColor = fill.property("ADBE Vector Fill Color");
fillColor.setValue([0, 0, 1, 1]);  // Blue
```

### Star

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add star group
var starGroup = contents.addProperty("ADBE Vector Group");
var starContents = starGroup.property("ADBE Vectors Group");

// Add star path
var starPath = starContents.addProperty("ADBE Vector Shape - Star");
starPath.name = "Star";

// Set star properties
var points = starPath.property("ADBE Vector Star Points");
points.setValue(5);

var innerRadius = starPath.property("ADBE Vector Star Inner Radius");
innerRadius.setValue(40);  // Non-zero for star

var outerRadius = starPath.property("ADBE Vector Star Outer Radius");
outerRadius.setValue(80);

var rotation = starPath.property("ADBE Vector Star Rotation");
rotation.setValue(0);

var roundness = starPath.property("ADBE Vector Star Roundness");
roundness.setValue(20);
```

### Bezier Path (Custom Shape)

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add shape group
var shapeGroup = contents.addProperty("ADBE Vector Group");
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add path
var path = shapeContents.addProperty("ADBE Vector Shape - Group");
path.name = "Custom Path";

// Create shape object
var shape = new Shape();

// Define vertices
shape.vertices = [
    [0, -50],      // Top
    [30, 0],       // Right
    [0, 50],       // Bottom
    [-30, 0]       // Left
];

// Define in tangents (Bezier handles)
shape.inTangents = [
    [-15, 0],
    [0, -15],
    [15, 0],
    [0, 15]
];

// Define out tangents
shape.outTangents = [
    [15, 0],
    [0, 15],
    [-15, 0],
    [0, -15]
];

// Set closed path
shape.closed = true;

// Apply shape
path.property("ADBE Vector Shape").setValue(shape);
```

### Path from Mask

```javascript
// Copy mask path to shape
var sourceLayer = comp.layer(1);
var mask = sourceLayer.property("Masks").property("Mask 1");
var maskPath = mask.property("Mask Path");

var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var shapeGroup = contents.addProperty("ADBE Vector Group");
var shapeContents = shapeGroup.property("ADBE Vectors Group");
var path = shapeContents.addProperty("ADBE Vector Shape - Group");

// Get mask shape at time
var maskShape = maskPath.valueAtTime(0, false);
path.property("ADBE Vector Shape").setValue(maskShape);
```

## Fill and Stroke

### Fill Properties

```javascript
var shapeGroup = contents.addProperty("ADBE Vector Group");
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add fill
var fill = shapeContents.addProperty("ADBE Vector Graphic - Fill");
fill.name = "My Fill";

// Fill color [R, G, B, A] 0.0-1.0
var fillColor = fill.property("ADBE Vector Fill Color");
fillColor.setValue([1, 0.5, 0, 1]);  // Orange

// Fill rule
var fillRule = fill.property("ADBE Vector Fill Rule");
fillRule.setValue(1);  // 1 = Non-Zero, 2 = Even-Odd

// Fill opacity (0-100)
var fillOpacity = fill.property("ADBE Vector Fill Opacity");
fillOpacity.setValue(80);
```

### Stroke Properties

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add stroke
var stroke = shapeContents.addProperty("ADBE Vector Graphic - Stroke");
stroke.name = "My Stroke";

// Stroke color
var strokeColor = stroke.property("ADBE Vector Stroke Color");
strokeColor.setValue([0, 0, 0, 1]);  // Black

// Stroke width
var strokeWidth = stroke.property("ADBE Vector Stroke Width");
strokeWidth.setValue(3);

// Stroke opacity (0-100)
var strokeOpacity = stroke.property("ADBE Vector Stroke Opacity");
strokeOpacity.setValue(100);

// Line cap
var lineCap = stroke.property("ADBE Vector Stroke Line Cap");
lineCap.setValue(1);  // 1=Butt, 2=Round, 3=Square

// Line join
var lineJoin = stroke.property("ADBE Vector Stroke Line Join");
lineJoin.setValue(1);  // 1=Miter, 2=Round, 3=Bevel

// Miter limit
var miterLimit = stroke.property("ADBE Vector Stroke Miter Limit");
miterLimit.setValue(4);

// Dashes
var dashes = stroke.property("ADBE Vector Stroke Dashes");
var dash = dashes.addProperty("ADBE Vector Stroke Dash");
dash.property("ADBE Vector Stroke Dash Length").setValue(10);
var gap = dashes.addProperty("ADBE Vector Stroke Gap");
gap.property("ADBE Vector Stroke Gap Length").setValue(5);
var offset = stroke.property("ADBE Vector Stroke Dash Offset");
offset.setValue(0);
```

### Multiple Fills and Strokes

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add multiple fills for layered effect
var fill1 = shapeContents.addProperty("ADBE Vector Graphic - Fill");
fill1.property("ADBE Vector Fill Color").setValue([1, 0, 0, 1]);

var fill2 = shapeContents.addProperty("ADBE Vector Graphic - Fill");
fill2.property("ADBE Vector Fill Color").setValue([0, 0, 1, 0.5]);  // Semi-transparent

// Order matters - first item is drawn first
fill1.moveToBeginning();  // Fill1 drawn first (bottom)
fill2.moveToEnd();        // Fill2 drawn second (top)
```

## Shape Modifiers

### Trim Paths

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add trim paths modifier
var trim = shapeContents.addProperty("ADBE Vector Filter - Trim");
trim.name = "Trim Paths";

// Trim start (0-100%)
var start = trim.property("ADBE Vector Trim Start");
start.setValue(0);

// Trim end (0-100%)
var end = trim.property("ADBE Vector Trim End");
end.setValue(100);

// Trim offset (0-100%)
var offset = trim.property("ADBE Vector Trim Offset");
offset.setValue(0);

// Trim type
var trimType = trim.property("ADBE Vector Trim Type");
trimType.setValue(1);  // 1=Simultaneously, 2=Individually

// Animate trim for drawing effect
end.setValueAtTime(0, 0);
end.setValueAtTime(2, 100);
```

### Round Corners

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add round corners modifier
var roundCorners = shapeContents.addProperty("ADBE Vector Filter - RC");
roundCorners.name = "Round Corners";

// Radius
var radius = roundCorners.property("ADBE Vector RoundCorner Radius");
radius.setValue(15);
```

### Pucker & Bloat

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add pucker & bloat
var puckerBloat = shapeContents.addProperty("ADBE Vector Filter - PB");
puckerBloat.name = "Pucker Bloat";

// Amount (-100 to 100)
var amount = puckerBloat.property("ADBE Vector PuckerBloat Amount");
amount.setValue(20);  // Positive = bloat, Negative = pucker
```

### Zig Zag

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add zig zag
var zigZag = shapeContents.addProperty("ADBE Vector Filter - Zigzag");
zigZag.name = "Zig Zag";

// Size
var size = zigZag.property("ADBE Vector Zigzag Size");
size.setValue(10);

// Ridges per segment
var ridges = zigZag.property("ADBE Vector Zigzag Detail");
ridges.setValue(5);

// Type
var zigType = zigZag.property("ADBE Vector Zigzag Type");
zigType.setValue(1);  // 1=Smooth, 2=Point
```

### Offset Paths

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add offset paths
var offsetPaths = shapeContents.addProperty("ADBE Vector Filter - Offset");
offsetPaths.name = "Offset Paths";

// Amount
var amount = offsetPaths.property("ADBE Vector Offset Amount");
amount.setValue(10);

// Line join
var lineJoin = offsetPaths.property("ADBE Vector Offset Line Join");
lineJoin.setValue(1);  // 1=Miter, 2=Round, 3=Bevel

// Miter limit
var miterLimit = offsetPaths.property("ADBE Vector Offset Miter Limit");
miterLimit.setValue(4);
```

### Repeater

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add repeater
var repeater = shapeContents.addProperty("ADBE Vector Filter - Repeater");
repeater.name = "Repeater";

// Copies
var copies = repeater.property("ADBE Vector Repeater Copies");
copies.setValue(5);

// Offset
var offset = repeater.property("ADBE Vector Repeater Offset");
offset.setValue(0);

// Composite
var composite = repeater.property("ADBE Vector Repeater Composite");
composite.setValue(1);  // 1=Above, 2=Below

// Repeater transform
var repeaterTransform = repeater.property("ADBE Vector Repeater Transform");
var repPosition = repeaterTransform.property("ADBE Vector Position");
repPosition.setValue([50, 0]);  // Offset each copy
var repScale = repeaterTransform.property("ADBE Vector Scale");
repScale.setValue([90, 90]);  // Scale down each copy
var repOpacity = repeaterTransform.property("ADBE Vector Repeater Opacity");
repOpacity.setValue(80);  // Fade each copy
```

### Twist

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add twist
var twist = shapeContents.addProperty("ADBE Vector Filter - Twist");
twist.name = "Twist";

// Angle
var angle = twist.property("ADBE Vector Twist Angle");
angle.setValue(180);

// Center
var center = twist.property("ADBE Vector Twist Center");
center.setValue([0, 0]);
```

### Warp

```javascript
var shapeContents = shapeGroup.property("ADBE Vectors Group");

// Add warp
var warp = shapeContents.addProperty("ADBE Vector Filter - Warp");
warp.name = "Warp";

// Warp properties
var horizontal = warp.property("ADBE Vector Warp Horizontal");
horizontal.setValue(0);
var vertical = warp.property("ADBE Vector Warp Vertical");
vertical.setValue(20);
```

## Shape Match Names Reference

### Shape Types
- `ADBE Vector Shape - Rect` - Rectangle
- `ADBE Vector Shape - Ellipse` - Ellipse
- `ADBE Vector Shape - Star` - Star/Polygon
- `ADBE Vector Shape - Group` - Bezier Path

### Graphics
- `ADBE Vector Graphic - Fill` - Fill
- `ADBE Vector Graphic - Stroke` - Stroke
- `ADBE Vector Graphic - GFill` - Gradient Fill
- `ADBE Vector Graphic - GStroke` - Gradient Stroke

### Modifiers (Filters)
- `ADBE Vector Filter - Trim` - Trim Paths
- `ADBE Vector Filter - RC` - Round Corners
- `ADBE Vector Filter - PB` - Pucker & Bloat
- `ADBE Vector Filter - Zigzag` - Zig Zag
- `ADBE Vector Filter - Offset` - Offset Paths
- `ADBE Vector Filter - Repeater` - Repeater
- `ADBE Vector Filter - Twist` - Twist
- `ADBE Vector Filter - Warp` - Warp
- `ADBE Vector Filter - Merge` - Merge Paths

### Transform
- `ADBE Vector Transform Group` - Shape transform
- `ADBE Vector Position` - Position
- `ADBE Vector Scale` - Scale
- `ADBE Vector Rotation` - Rotation
- `ADBE Vector Opacity` - Opacity
- `ADBE Vector Anchor` - Anchor Point

### Rectangle Properties
- `ADBE Vector Rect Size` - Size
- `ADBE Vector Rect Position` - Position
- `ADBE Vector Rect Roundness` - Roundness

### Ellipse Properties
- `ADBE Vector Ellipse Size` - Size
- `ADBE Vector Ellipse Position` - Position

### Star Properties
- `ADBE Vector Star Points` - Points
- `ADBE Vector Star Inner Radius` - Inner Radius
- `ADBE Vector Star Outer Radius` - Outer Radius
- `ADBE Vector Star Rotation` - Rotation
- `ADBE Vector Star Roundness` - Roundness

### Path Properties
- `ADBE Vector Shape` - Shape object

### Fill Properties
- `ADBE Vector Fill Color` - Color [R, G, B, A]
- `ADBE Vector Fill Opacity` - Opacity (0-100)
- `ADBE Vector Fill Rule` - Fill Rule (1=Non-Zero, 2=Even-Odd)

### Stroke Properties
- `ADBE Vector Stroke Color` - Color
- `ADBE Vector Stroke Width` - Width
- `ADBE Vector Stroke Opacity` - Opacity (0-100)
- `ADBE Vector Stroke Line Cap` - Line Cap
- `ADBE Vector Stroke Line Join` - Line Join
- `ADBE Vector Stroke Miter Limit` - Miter Limit
- `ADBE Vector Stroke Dashes` - Dashes group
- `ADBE Vector Stroke Dash` - Dash element
- `ADBE Vector Stroke Gap` - Gap element
- `ADBE Vector Stroke Dash Offset` - Dash Offset

### Repeater Properties
- `ADBE Vector Repeater Copies` - Copies
- `ADBE Vector Repeater Offset` - Offset
- `ADBE Vector Repeater Composite` - Composite
- `ADBE Vector Repeater Transform` - Transform group
- `ADBE Vector Repeater Opacity` - Opacity

## Shape Layer Organization

### Multiple Shapes in One Layer

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Add first shape
var group1 = contents.addProperty("ADBE Vector Group");
group1.name = "Shape 1";
var group1Contents = group1.property("ADBE Vectors Group");
var path1 = group1Contents.addProperty("ADBE Vector Shape - Rect");
path1.property("ADBE Vector Rect Size").setValue([100, 100]);
var fill1 = group1Contents.addProperty("ADBE Vector Graphic - Fill");
fill1.property("ADBE Vector Fill Color").setValue([1, 0, 0, 1]);

// Add second shape
var group2 = contents.addProperty("ADBE Vector Group");
group2.name = "Shape 2";
var group2Contents = group2.property("ADBE Vectors Group");
var path2 = group2Contents.addProperty("ADBE Vector Shape - Ellipse");
path2.property("ADBE Vector Ellipse Size").setValue([80, 80]);
var fill2 = group2Contents.addProperty("ADBE Vector Graphic - Fill");
fill2.property("ADBE Vector Fill Color").setValue([0, 1, 0, 1]);

// Position shapes
var transform1 = group1.property("ADBE Vector Transform Group");
transform1.property("ADBE Vector Position").setValue([200, 540]);

var transform2 = group2.property("ADBE Vector Transform Group");
transform2.property("ADBE Vector Position").setValue([400, 540]);
```

### Shape Layer with Multiple Groups

```javascript
// Create complex shape with multiple elements
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

// Background rectangle
var bgGroup = contents.addProperty("ADBE Vector Group");
bgGroup.name = "Background";
var bgContents = bgGroup.property("ADBE Vectors Group");
var bgRect = bgContents.addProperty("ADBE Vector Shape - Rect");
bgRect.property("ADBE Vector Rect Size").setValue([400, 200]);
var bgFill = bgContents.addProperty("ADBE Vector Graphic - Fill");
bgFill.property("ADBE Vector Fill Color").setValue([0.1, 0.1, 0.1, 1]);

// Icon circle
var iconGroup = contents.addProperty("ADBE Vector Group");
iconGroup.name = "Icon";
var iconContents = iconGroup.property("ADBE Vectors Group");
var iconEllipse = iconContents.addProperty("ADBE Vector Shape - Ellipse");
iconEllipse.property("ADBE Vector Ellipse Size").setValue([50, 50]);
var iconFill = iconContents.addProperty("ADBE Vector Graphic - Fill");
iconFill.property("ADBE Vector Fill Color").setValue([1, 1, 1, 1]);

// Position icon
var iconTransform = iconGroup.property("ADBE Vector Transform Group");
iconTransform.property("ADBE Vector Position").setValue([0, 0]);
```

## Shape Animation

### Animate Shape Properties

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");

// Rectangle
var rect = groupContents.addProperty("ADBE Vector Shape - Rect");
var size = rect.property("ADBE Vector Rect Size");

// Animate size
size.setValueAtTime(0, [50, 50]);
size.setValueAtTime(1, [200, 200]);
size.setValueAtTime(2, [100, 100]);

// Animate position
var position = rect.property("ADBE Vector Rect Position");
position.setValueAtTime(0, [-100, 0]);
position.setValueAtTime(1, [0, 0]);
position.setValueAtTime(2, [100, 0]);

// Animate roundness
var roundness = rect.property("ADBE Vector Rect Roundness");
roundness.setValueAtTime(0, 0);
roundness.setValueAtTime(1, 25);
roundness.setValueAtTime(2, 50);
```

### Animate Trim Paths

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");

// Add path
var path = groupContents.addProperty("ADBE Vector Shape - Ellipse");
path.property("ADBE Vector Ellipse Size").setValue([200, 200]);

// Add stroke
var stroke = groupContents.addProperty("ADBE Vector Graphic - Stroke");
stroke.property("ADBE Vector Stroke Width").setValue(5);
stroke.property("ADBE Vector Stroke Color").setValue([1, 1, 1, 1]);

// Add trim paths
var trim = groupContents.addProperty("ADBE Vector Filter - Trim");
var trimEnd = trim.property("ADBE Vector Trim End");

// Animate drawing
trimEnd.setValueAtTime(0, 0);
trimEnd.setValueAtTime(2, 100);
```

### Animate Repeater

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");

// Add shape
var rect = groupContents.addProperty("ADBE Vector Shape - Rect");
rect.property("ADBE Vector Rect Size").setValue([30, 30]);
var fill = groupContents.addProperty("ADBE Vector Graphic - Fill");
fill.property("ADBE Vector Fill Color").setValue([1, 0.5, 0, 1]);

// Add repeater
var repeater = groupContents.addProperty("ADBE Vector Filter - Repeater");
var copies = repeater.property("ADBE Vector Repeater Copies");
var repTransform = repeater.property("ADBE Vector Repeater Transform");
var repPosition = repTransform.property("ADBE Vector Position");
var repRotation = repTransform.property("ADBE Vector Rotation");

// Animate copies
copies.setValueAtTime(0, 1);
copies.setValueAtTime(2, 10);

// Set repeater transform
repPosition.setValue([40, 0]);
repRotation.setValue(36);
```

### Morphing Shapes

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");
var path = groupContents.addProperty("ADBE Vector Shape - Group");

// Create starting shape (square)
var shape1 = new Shape();
shape1.vertices = [[-50, -50], [50, -50], [50, 50], [-50, 50]];
shape1.inTangents = [[0, 0], [0, 0], [0, 0], [0, 0]];
shape1.outTangents = [[0, 0], [0, 0], [0, 0], [0, 0]];
shape1.closed = true;

// Create ending shape (circle approximation)
var shape2 = new Shape();
shape2.vertices = [
    [0, -50],
    [35, -35],
    [50, 0],
    [35, 35],
    [0, 50],
    [-35, 35],
    [-50, 0],
    [-35, -35]
];
shape2.inTangents = [
    [-15, 0],
    [0, -15],
    [0, 15],
    [-15, 0],
    [15, 0],
    [0, -15],
    [0, 15],
    [15, 0]
];
shape2.outTangents = [
    [15, 0],
    [0, 15],
    [0, -15],
    [15, 0],
    [-15, 0],
    [0, 15],
    [0, -15],
    [-15, 0]
];
shape2.closed = true;

// Animate morph
path.property("ADBE Vector Shape").setValueAtTime(0, shape1);
path.property("ADBE Vector Shape").setValueAtTime(2, shape2);
```

## Common Patterns

### Create Grid of Shapes

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

var rows = 4;
var cols = 6;
var spacing = 60;
var startX = -((cols - 1) * spacing) / 2;
var startY = -((rows - 1) * spacing) / 2;

for (var r = 0; r < rows; r++) {
    for (var c = 0; c < cols; c++) {
        var group = contents.addProperty("ADBE Vector Group");
        group.name = "Cell_" + r + "_" + c;
        var groupContents = group.property("ADBE Vectors Group");
        
        // Add rectangle
        var rect = groupContents.addProperty("ADBE Vector Shape - Rect");
        rect.property("ADBE Vector Rect Size").setValue([40, 40]);
        
        // Add fill with varying color
        var fill = groupContents.addProperty("ADBE Vector Graphic - Fill");
        var hue = (r * cols + c) / (rows * cols);
        fill.property("ADBE Vector Fill Color").setValue([hue, 0.5, 0.5, 1]);
        
        // Position
        var transform = group.property("ADBE Vector Transform Group");
        transform.property("ADBE Vector Position").setValue([
            startX + c * spacing,
            startY + r * spacing
        ]);
    }
}
```

### Create Circular Arrangement

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");

var count = 12;
var radius = 150;

for (var i = 0; i < count; i++) {
    var angle = (i / count) * Math.PI * 2;
    var x = Math.cos(angle) * radius;
    var y = Math.sin(angle) * radius;
    
    var group = contents.addProperty("ADBE Vector Group");
    var groupContents = group.property("ADBE Vectors Group");
    
    // Add circle
    var ellipse = groupContents.addProperty("ADBE Vector Shape - Ellipse");
    ellipse.property("ADBE Vector Ellipse Size").setValue([30, 30]);
    
    // Add fill
    var fill = groupContents.addProperty("ADBE Vector Graphic - Fill");
    fill.property("ADBE Vector Fill Color").setValue([
        Math.cos(angle) * 0.5 + 0.5,
        Math.sin(angle) * 0.5 + 0.5,
        0.5,
        1
    ]);
    
    // Position
    var transform = group.property("ADBE Vector Transform Group");
    transform.property("ADBE Vector Position").setValue([x, y]);
}
```

### Animated Loading Spinner

```javascript
var shapeLayer = comp.layers.addShape();
var contents = shapeLayer.property("Contents");
var group = contents.addProperty("ADBE Vector Group");
var groupContents = group.property("ADBE Vectors Group");

// Add arc (using ellipse with trim)
var ellipse = groupContents.addProperty("ADBE Vector Shape - Ellipse");
ellipse.property("ADBE Vector Ellipse Size").setValue([100, 100]);

// Add stroke
var stroke = groupContents.addProperty("ADBE Vector Graphic - Stroke");
stroke.property("ADBE Vector Stroke Width").setValue(8);
stroke.property("ADBE Vector Stroke Color").setValue([1, 1, 1, 1]);
stroke.property("ADBE Vector Stroke Line Cap").setValue(2);  // Round cap

// Add trim paths
var trim = groupContents.addProperty("ADBE Vector Filter - Trim");
var start = trim.property("ADBE Vector Trim Start");
var end = trim.property("ADBE Vector Trim End");
var offset = trim.property("ADBE Vector Trim Offset");

// Animate
start.setValueAtTime(0, 0);
start.setValueAtTime(1, 75);

end.setValueAtTime(0, 25);
end.setValueAtTime(1, 100);

offset.setValueAtTime(0, 0);
offset.setValueAtTime(1, 360);
```

## Best Practices

1. **Use shape groups** to organize multiple shapes within a layer
2. **Name your shape groups** for easier identification
3. **Use match names** for language-independent scripts
4. **Order matters** - items are drawn in order (first = bottom)
5. **Use repeaters** for efficient pattern creation
6. **Animate trim paths** for draw-on effects
7. **Use expressions** on shape properties for procedural animation
8. **Keep shape layers organized** with multiple groups vs multiple layers
9. **Use transform groups** within shapes for local transformations
10. **Consider using merge paths** for complex shape combinations

## Notes

- Shape layers are vector-based and resolution-independent
- Each shape group has its own transform properties
- Order of items in contents affects rendering order
- Modifiers affect all shapes above them in the stack
- Repeater is powerful for creating patterns efficiently
- Shape paths can be animated for morphing effects
- Use `new Shape()` to create custom bezier paths
- Fill and stroke can be animated independently
- Trim paths works on strokes, not fills
- Shape layer contents can be accessed via "Contents" property
