#target aftereffects

(function() {

    var data = loadData();
    if (!data) return;

    var s = data.settings;
    if (!app.project) app.newProject();
    var project = app.project;
    var W = s.width;
    var H = s.height;
    var FPS = s.fps;
    var DUR = s.total_duration;

    var mainComp = project.items.addComp(s.project_name, W, H, 1.0, DUR, FPS);
    mainComp.openInViewer();

    var layers = {};
    var bgOrder = [];
    var TRANSITION_COMP_DUR = 2.0;
    var transitionMaster = null;

    for (var i = 0; i < data.timeline.length; i++) {
        var e = data.timeline[i];
        try {
            switch (e.type) {
                case "intro":        buildIntro(e); break;
                case "video":        buildVideo(e); break;
                case "solid":        buildSolid(e); break;
                case "audio":        buildAudio(e); break;
                case "ken_burns":    buildKenBurns(e); break;
                case "film_grain":   buildFilmGrain(e); break;
                case "text_overlay": buildTextOverlay(e); break;
                case "photo_overlay":buildPhotoOverlay(e); break;
                case "transition":   buildTransition(e); break;
                case "music":        buildMusic(e); break;
                case "logo":         buildLogo(e); break;
                default: $.writeln("Unknown type: " + e.type);
            }
        } catch(err) {
            $.writeln("Error [" + e.type + "]: " + err.toString() + " | entry=" + i);
            alert("Error in [" + e.type + "] entry #" + i + ": " + err.toString());
        }
    }

    var saveFile = new File(s.save_path);
    project.save(saveFile);
    $.writeln("Done: " + s.project_name + " | " + DUR.toFixed(1) + "s");


    // ====================== DATA LOADING ======================

    function loadData() {
        var scriptDir = getScriptDir();
        if (scriptDir) {
            var f = new File(scriptDir + "/ae_project.json");
            var d = readJson(f);
            if (d) return d;
        }
        var dlg = File.openDialog("Select ae_project.json", "JSON:*.json");
        if (dlg) return readJson(dlg);
        $.writeln("No JSON file found");
        return null;
    }

    function getScriptDir() {
        try { return new File($.fileName).parent.fsName; } catch(e) { return null; }
    }

    function readJson(file) {
        try {
            file.encoding = "UTF-8";
            file.open("r");
            var raw = file.read();
            file.close();
            return eval("(" + raw + ")");
        } catch(e) {
            $.writeln("JSON parse error: " + e);
            return null;
        }
    }


    // ====================== CORE BUILDERS ======================

    function buildIntro(e) {
        var comp = project.items.addComp("Intro", W, H, 1.0, e.duration, FPS);
        var bg = comp.layers.addSolid([0.03, 0.03, 0.06], "Intro BG", W, H, 1.0);
        bg.outPoint = e.duration;

        var line = comp.layers.addSolid([0.4, 0.4, 0.5], "Line", W, H, 1.0);
        line.property("Scale").setValue([40, 0.3]);
        line.property("Position").setValue([W / 2, H / 2 + 50]);
        fade(line, 0, 0.8, e.duration - 0.8, e.duration);

        var title = comp.layers.addText(e.title);
        title.name = "Intro Title";
        setStyle(title, e.title_font, e.title_size, "CENTER_JUSTIFY", [1, 1, 1]);
        title.property("Position").setValue([W / 2, H / 2 - 30]);
        fade(title, 0, 0.6, e.duration - 0.6, e.duration);

        if (e.subtitle) {
            var sub = comp.layers.addText(e.subtitle);
            sub.name = "Intro Subtitle";
            setStyle(sub, e.subtitle_font, e.subtitle_size, "CENTER_JUSTIFY", [0.6, 0.6, 0.7]);
            sub.property("Position").setValue([W / 2, H / 2 + 90]);
            fade(sub, 0, 1.0, e.duration - 0.6, e.duration);
        }

        var layer = mainComp.layers.add(comp);
        layer.name = "Intro";
        layer.startTime = e.at;
        layer.outPoint = e.at + e.duration;
    }

    function fitToCompCover(footage, factor) {
        var sx = W / footage.width * 100;
        var sy = H / footage.height * 100;
        var s = Math.max(sx, sy) * factor;
        return [s, s];
    }

    function fitToCompContain(footage, factor) {
        var sx = W / footage.width * 100;
        var sy = H / footage.height * 100;
        var s = Math.min(sx, sy) * factor;
        return [s, s];
    }

    function fitToComp120(footage) {
        return fitToCompCover(footage, 1.2);
    }

    function buildVideo(e) {
        var footage = tryImport(e.file);
        if (!footage) {
            var layer = mainComp.layers.addSolid([0.15, 0.15, 0.25], e.label || e.id, W, H, 1.0, e.duration);
            layer.startTime = e.at;
            layer.outPoint = e.at + e.duration;
            layer.property("Scale").setValue([120, 120]);
            if (e.id) { layers[e.id] = layer; bgOrder.push(e.id); }
            return;
        }
        var layer = addLayer(mainComp, footage, e.at, e.duration, e.label || e.id);
        layer.property("Scale").setValue(fitToComp120(footage));
        layer.property("Position").setValue([W / 2, H / 2]);
        var anchorX = footage.width / 2;
        var anchorY = footage.height / 2;
        layer.property("Anchor Point").setValue([anchorX, anchorY]);
        if (e.id) { layers[e.id] = layer; bgOrder.push(e.id); }
    }

    function buildSolid(e) {
        var layer = mainComp.layers.addSolid(e.color, e.label || e.id, W, H, 1.0, e.duration);
        layer.startTime = e.at;
        layer.outPoint = e.at + e.duration;
        layer.property("Scale").setValue([120, 120]);
        if (e.id) { layers[e.id] = layer; bgOrder.push(e.id); }
    }

    function buildAudio(e) {
        var footage = tryImport(e.file);
        if (!footage) return;
        var layer = addLayer(mainComp, footage, e.at, e.duration, "Audio");
        layer.audioEnabled = true;
    }

    function buildKenBurns(e) {
        var layer = layers[e.target];
        if (!layer) return;
        var sc = layer.property("Scale");
        sc.setValueAtTime(e.at, [e.start_scale, e.start_scale]);
        sc.setValueAtTime(e.at + e.duration, [e.end_scale, e.end_scale]);
        var pos = layer.property("Position");
        pos.setValueAtTime(e.at, [W / 2, H / 2]);
        pos.setValueAtTime(e.at + e.duration, [W / 2 + e.pan_x, H / 2 + e.pan_y]);
    }

    function buildFilmGrain(e) {
        var grainComp = findCompByName("Film Grain");
        if (grainComp) {
            var layer = mainComp.layers.add(grainComp);
            layer.name = "Film Grain";
            layer.startTime = e.at;
            layer.outPoint = e.at + e.duration;
            layer.property("Opacity").setValue(e.opacity);
            if (e.blend_mode === "screen") layer.blendingMode = BlendingMode.SCREEN;
            else if (e.blend_mode === "multiply") layer.blendingMode = BlendingMode.MULTIPLY;
            else if (e.blend_mode === "soft_light") layer.blendingMode = BlendingMode.SOFT_LIGHT;
            else layer.blendingMode = BlendingMode.OVERLAY;
            return;
        }

        var footage = tryImport(e.file);
        if (!footage) return;
        var comp = project.items.addComp("Grain Loop", W, H, 1.0, e.duration, FPS);
        var inner = comp.layers.add(footage);
        inner.timeRemapEnabled = true;
        var tr = inner.property("Time Remap");
        var fd = footage.duration;
        tr.setValueAtTime(0, 0);
        tr.setValueAtTime(fd - 0.01, fd - 0.01);
        tr.expression = "loopOut('cycle')";
        inner.outPoint = e.duration;

        var layer = mainComp.layers.add(comp);
        layer.name = "Film Grain";
        layer.startTime = e.at;
        layer.outPoint = e.at + e.duration;
        if (e.blend_mode === "screen") layer.blendingMode = BlendingMode.SCREEN;
        else if (e.blend_mode === "multiply") layer.blendingMode = BlendingMode.MULTIPLY;
        else if (e.blend_mode === "soft_light") layer.blendingMode = BlendingMode.SOFT_LIGHT;
        else layer.blendingMode = BlendingMode.OVERLAY;
        layer.property("Opacity").setValue(e.opacity);
        layer.property("Scale").setValue([e.scale, e.scale]);
    }

    function buildTextOverlay(e) {
        var st = e.style;
        if (e.template === "thesis" && st.background_enabled) {
            var txt = mainComp.layers.addText(e.text);
            txt.name = "Thesis";
            txt.startTime = e.at;
            txt.outPoint = e.at + e.duration;
            setStyle(txt, st.font, st.font_size, st.justification, st.fill_color);
            txt.property("Position").setValue([W / 2, st.y_pos]);
            fade(txt, e.at, e.at + st.fade_in, e.at + e.duration - st.fade_out, e.at + e.duration);

            var txtRect = txt.sourceRectAtTime(e.at, false);
            var padding = 40;
            var bgW = (txtRect.width + padding * 2) / W * 100;
            var bgH = (txtRect.height + padding * 2) / H * 100;
            var bgCx = W / 2 + txtRect.left + txtRect.width / 2;
            var bgCy = st.y_pos + txtRect.top + txtRect.height / 2;
            var bgBox = mainComp.layers.addSolid(st.background_color, "Thesis BG", W, H, 1.0);
            bgBox.startTime = e.at;
            bgBox.outPoint = e.at + e.duration;
            bgBox.property("Opacity").setValue(st.background_opacity);
            bgBox.property("Scale").setValue([bgW, bgH]);
            bgBox.property("Position").setValue([bgCx, bgCy]);
            bgBox.moveAfter(txt);
            fade(bgBox, e.at, e.at + st.fade_in, e.at + e.duration - st.fade_out, e.at + e.duration);

        } else if (e.template === "quote") {
            var qc = project.items.addComp("Quote", W, H, 1.0, e.duration, FPS);
            var dimBg = qc.layers.addSolid([0.05, 0.05, 0.08], "Dim BG", W, H, 1.0);
            dimBg.property("Opacity").setValue(st.background_opacity);

            if (e.photo_file) {
                var photo = tryImport(e.photo_file);
                if (photo) {
                    var pLayer = qc.layers.add(photo);
                    pLayer.name = "Person Photo";
                    pLayer.property("Position").setValue([st.photo_x, st.photo_y]);
                    pLayer.property("Scale").setValue(fitToCompContain(photo, 0.5));
                }
            }

            var hasPhoto = e.photo_file && photo;
            var boxW = hasPhoto ? W * 0.35 : W * 0.7;
            var boxH = H * 0.5;
            var qText = qc.layers.addBoxText([boxW, boxH], "\u201C" + e.text + "\u201D");
            qText.name = "Quote Text";
            setStyle(qText, st.font, st.font_size_quote, "LEFT_JUSTIFY", st.quote_color);
            qText.property("Position").setValue([st.text_x, st.text_y]);
            fade(qText, 0, 0.5, e.duration - 0.5, e.duration);

            if (e.source) {
                var nText = qc.layers.addBoxText([boxW, 60], "\u2014 " + e.source);
                nText.name = "Person Name";
                setStyle(nText, st.font, st.font_size_name, "LEFT_JUSTIFY", st.name_color);
                nText.property("Position").setValue([st.text_x, st.name_y]);
            }

            var compLayer = mainComp.layers.add(qc);
            compLayer.name = "Quote";
            compLayer.startTime = e.at;
            compLayer.outPoint = e.at + e.duration;

        } else {
            var txt2 = mainComp.layers.addText(e.text);
            txt2.name = e.template || "Text";
            txt2.startTime = e.at;
            txt2.outPoint = e.at + e.duration;
            setStyle(txt2, st.font, st.font_size, st.justification, st.fill_color);
            txt2.property("Position").setValue([W / 2, st.y_pos]);
        }
    }

    function buildPhotoOverlay(e) {
        var st = e.style;
        if (st.shadow) {
            var shadow = mainComp.layers.addSolid([0, 0, 0], "Shadow", W, H, 1.0);
            shadow.startTime = e.at + st.fade_duration;
            shadow.outPoint = e.at + e.duration - st.fade_duration;
            shadow.property("Opacity").setValue(40);
            shadow.property("Scale").setValue([200, 200]);
            shadow.property("Position").setValue([st.position_x + 5, st.position_y + 5]);
            try {
                var blur = shadow.property("Effects").addProperty("ADBE Gaussian Blur 2");
                blur.property("Blurriness").setValue(20);
            } catch(e2) {}
        }

        var footage = tryImport(e.file);
        if (!footage) {
            var fallback = mainComp.layers.addText("Photo");
            fallback.name = "Photo (missing)";
            fallback.startTime = e.at;
            fallback.outPoint = e.at + e.duration;
            fallback.property("Position").setValue([st.position_x, st.position_y]);
            return;
        }
        var layer = addLayer(mainComp, footage, e.at, e.duration, "Photo");
        layer.property("Position").setValue([st.position_x, st.position_y]);
        layer.property("Scale").setValue(fitToCompContain(footage, 0.5));
        fade(layer, e.at, e.at + st.fade_duration, e.at + e.duration - st.fade_duration, e.at + e.duration);
    }

    function findTransitionComp() {
        if (transitionMaster) return transitionMaster;
        for (var i = 1; i <= project.numItems; i++) {
            var item = project.item(i);
            if (item instanceof CompItem && item.name === "Transition") {
                transitionMaster = item;
                return transitionMaster;
            }
        }
        $.writeln("Warning: Transition comp not found in project");
        return null;
    }

    function buildTransition(e) {
        var transComp = findCompByName("Transition");
        if (!transComp) {
            $.writeln("Error: Transition comp not found");
            return;
        }

        var transLayer = mainComp.layers.add(transComp);
        transLayer.name = "Transition " + e.from + "->" + e.to;
        transLayer.startTime = e.at;
        transLayer.outPoint = e.at + e.duration;
        transLayer.collapseTransformation = true;
    }

    function findCompByName(name) {
        for (var i = 1; i <= project.numItems; i++) {
            var item = project.item(i);
            if (item instanceof CompItem && item.name === name) {
                return item;
            }
        }
        return null;
    }

    function buildMusic(e) {
        var footage = tryImport(e.file);
        if (!footage) return;
        var layer = addLayer(mainComp, footage, e.at, e.duration, "Music");
        layer.audioEnabled = true;
        try {
            var vol = layer.property("Audio").property("Audio Levels");
            if (vol) {
                var db = (e.volume / 100 - 1) * 48;
                vol.setValue([db, db]);
            }
        } catch(e2) {}
        layer.timeRemapEnabled = true;
        var tr = layer.property("Time Remap");
        if (tr) {
            var md = footage.duration;
            tr.setValueAtTime(0, 0);
            tr.setValueAtTime(md - 0.01, md - 0.01);
            tr.expression = "loopOut('cycle')";
        }
    }

    function buildLogo(e) {
        var footage = tryImport(e.file);
        if (!footage) return;
        var layer = addLayer(mainComp, footage, e.at, e.duration, "Logo");
        layer.property("Position").setValue([e.position_x, e.position_y]);
        layer.property("Scale").setValue([e.scale, e.scale]);
        layer.property("Opacity").setValue(e.opacity);
    }


    // ====================== UTILITIES ======================

    function tryImport(path) {
        try {
            var io = new ImportOptions();
            io.file = new File(path);
            return project.importFile(io);
        } catch(err) {
            $.writeln("Import failed: " + path + " | " + err.toString());
            return null;
        }
    }

    function importFile(path) {
        var result = tryImport(path);
        if (!result) throw new Error("Cannot import: " + path);
        return result;
    }

    function addLayer(comp, footage, start, dur, name) {
        var layer = comp.layers.add(footage);
        layer.name = name;
        layer.startTime = start;
        layer.outPoint = start + dur;
        return layer;
    }

    function setStyle(textLayer, font, fontSize, justification, fillColor) {
        var tp = textLayer.property("Source Text");
        var td = tp.value;
        td.resetCharStyle();
        td.applyFill = true;
        td.applyStroke = false;
        td.fillColor = fillColor;
        td.fontSize = fontSize;
        td.font = font;
        td.justification = ParagraphJustification[justification];
        tp.setValue(td);
    }

    function fade(layer, tIn, tFullIn, tFullOut, tOut) {
        var op = layer.property("Opacity");
        op.setValueAtTime(tIn, 0);
        op.setValueAtTime(tFullIn, 100);
        op.setValueAtTime(tFullOut, 100);
        op.setValueAtTime(tOut, 0);
    }

})();
