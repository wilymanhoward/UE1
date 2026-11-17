"""Build Wildwood's sparse, edge-anchored gameplay HUD using its existing native bindings."""

import unreal

PATH = "/Game/UI/WBP_HUD"
IVORY = unreal.LinearColor(0.91, 0.88, 0.76, 1.0)
GOLD = unreal.LinearColor(0.94, 0.77, 0.36, 1.0)
MUTED = unreal.LinearColor(0.67, 0.69, 0.63, 1.0)
SHADOW = unreal.LinearColor(0.015, 0.02, 0.015, 0.95)


def build():
    blueprint = unreal.load_asset(PATH)
    assert blueprint
    bound_names = {"FormIcon", "FormNameText", "NotesText", "PetalsText", "TimerText", "RestorationBar", "PromptText"}
    widgets = {widget.get_name(): widget for widget in unreal.ObjectIterator(unreal.Widget)
               if widget.get_outer() and widget.get_outer().get_outer() == blueprint}
    assert bound_names.issubset(widgets)
    required = {'RootCanvas','HUDSafeArea','WildernessLayout','ObjectiveShade','ObjectiveAccent',
                'QuestCategory','QuestHeading','ObjectiveNote','RestorationLabel','RestorationStart',
                'RestorationEnd','RunClock','FormShade','FormAccent','ActiveFormLabel','FormUnderline',
                'PetalMark','PetalCaption','PromptPanel','HintBackdrop','HintDiamond',
                'PromptTitleText','PromptKeyText','NoticePanel','NoticeText','NoticeDiamond'}
    assert required.issubset(widgets), f'Missing registered HUD widgets: {required - widgets.keys()}'
    canvas = widgets["RootCanvas"]
    tree = canvas.get_outer()
    blueprint.modify()
    tree.modify()
    for name in bound_names:
        widgets[name].remove_from_parent()
    canvas.clear_children()

    def make(kind, name):
        if name in widgets:
            widget = widgets[name]
            assert isinstance(widget, kind), name
            if isinstance(widget, unreal.PanelWidget):
                widget.clear_children()
        else:
            raise RuntimeError(f"HUD scaffold is missing registered widget {name}")
        widget.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
        return widget

    safe = make(unreal.SafeZone, "HUDSafeArea")
    slot = canvas.add_child_to_canvas(safe)
    slot.set_anchors(unreal.Anchors(unreal.Vector2D(0, 0), unreal.Vector2D(1, 1)))
    slot.set_offsets(unreal.Margin(32, 12, 32, 12))
    layout = make(unreal.CanvasPanel, "WildernessLayout")
    safe.add_child(layout)

    def place(widget, anchor, pos, size, align=(0, 0)):
        slot = layout.add_child_to_canvas(widget)
        slot.set_anchors(unreal.Anchors(unreal.Vector2D(*anchor), unreal.Vector2D(*anchor)))
        slot.set_alignment(unreal.Vector2D(*align))
        slot.set_position(unreal.Vector2D(*pos))
        slot.set_size(unreal.Vector2D(*size))
        return widget

    def text(name, content, point, anchor, pos, size, tint=IVORY, bold=False, spacing=0, justify=unreal.TextJustify.LEFT, align=(0, 0)):
        widget = widgets[name] if name in bound_names else make(unreal.TextBlock, name)
        widget.set_text(unreal.Text(content))
        font = widget.get_editor_property("font")
        font.set_editor_property("size", point)
        font.set_editor_property("font_object", unreal.load_asset('/Game/UI/Fonts/F_Wildwood'))
        font.set_editor_property("typeface_font_name", "Heading" if bold else "Regular")
        font.set_editor_property("letter_spacing", spacing)
        widget.set_font(font)
        widget.set_color_and_opacity(unreal.SlateColor(tint))
        widget.set_shadow_offset(unreal.Vector2D(1, 2))
        widget.set_shadow_color_and_opacity(SHADOW)
        widget.set_editor_property("justification", justify)
        place(widget, anchor, pos, size, align)
        return widget

    def line(name, anchor, pos, size, tint=GOLD, align=(0, 0)):
        image = make(unreal.Image, name)
        image.set_color_and_opacity(tint)
        return place(image, anchor, pos, size, align)

    def icon(name, texture, anchor, pos, size, tint=IVORY, align=(0, 0)):
        image = widgets[name] if name in bound_names else make(unreal.Image, name)
        image.set_brush_from_texture(unreal.load_asset(texture), False)
        image.set_color_and_opacity(tint)
        return place(image, anchor, pos, size, align)

    # Keep the objective open over the environment, as in the reference HUD.
    icon("ObjectiveShade", "/Game/UI/Textures/T_UI_Shade", (0, 0), (26, 29), (440, 165),
         unreal.LinearColor(1, 1, 1, 0.0))
    line("ObjectiveAccent", (0, 0), (46, 140), (6, 6), GOLD).set_render_transform_angle(45)
    text("QuestCategory", "Main Quest", 16, (0, 0), (46, 45), (330, 32), IVORY)
    text("QuestHeading", "REAWAKEN THE FOREST", 28, (0, 0), (46, 77), (430, 50), GOLD, True, 100)
    icon("ObjectiveNote", "/Game/UI/Textures/T_UI_Note", (0, 0), (47, 145), (17, 22), GOLD).set_render_opacity(0)
    text("NotesText", "Life Notes 0/20", 19, (0, 0), (65, 130), (340, 34))

    text("RestorationLabel", "FOREST RESTORATION", 14, (0.5, 0), (0, 28), (350, 26),
         MUTED, spacing=160, justify=unreal.TextJustify.CENTER, align=(0.5, 0))
    bar = widgets["RestorationBar"]
    bar.set_percent(0.0)
    bar.set_fill_color_and_opacity(GOLD)
    style = bar.get_editor_property("widget_style")
    for field, tint in (("background_image", unreal.LinearColor(0.10, 0.13, 0.11, 0.72)),
                        ("fill_image", unreal.LinearColor(1, 1, 1, 1))):
        brush = style.get_editor_property(field)
        brush.set_editor_property("draw_as", unreal.SlateBrushDrawType.IMAGE)
        brush.set_editor_property("tint_color", unreal.SlateColor(tint))
        style.set_editor_property(field, brush)
    bar.set_editor_property("widget_style", style)
    bar.set_editor_property("border_padding", unreal.Vector2D(0, 0))
    place(bar, (0.5, 0), (0, 61), (400, 3), (0.5, 0))
    line("RestorationStart", (0.5, 0), (-204, 58), (2, 9), MUTED)
    line("RestorationEnd", (0.5, 0), (202, 58), (2, 9), MUTED)

    text("TimerText", "0:00", 23, (1, 0), (-48, 38), (150, 40),
         IVORY, justify=unreal.TextJustify.RIGHT, align=(1, 0))
    icon("RunClock", "/Game/UI/Textures/T_UI_Clock", (1, 0), (-134, 47), (22, 22), MUTED)

    icon("FormShade", "/Game/UI/Textures/T_UI_Shade", (0, 1), (27, -141), (385, 107),
         unreal.LinearColor(1, 1, 1, 0))
    line("FormAccent", (0, 1), (63, -120), (63, 63), MUTED).set_render_opacity(0)
    icon("FormIcon", "/Game/UI/Textures/T_UI_FormSeed", (0, 1), (66, -116), (55, 55))
    text("ActiveFormLabel", "ACTIVE FORM", 10, (0, 1), (138, -120), (210, 18), MUTED, spacing=150)
    text("FormNameText", "Seed", 28, (0, 1), (138, -98), (245, 50), IVORY, True, 100)
    line("FormUnderline", (0, 1), (138, -45), (150, 2), GOLD)

    icon("PetalMark", "/Game/UI/Textures/T_UI_Petal", (1, 1), (-153, -94), (24, 28), GOLD)
    text("PetalCaption", "GOLDEN PETALS", 10, (1, 1), (-48, -119), (210, 18),
         MUTED, spacing=110, justify=unreal.TextJustify.RIGHT, align=(1, 0))
    text("PetalsText", "0", 23, (1, 1), (-48, -94), (72, 40),
         IVORY, justify=unreal.TextJustify.RIGHT, align=(1, 0))

    panel = make(unreal.CanvasPanel, 'PromptPanel')
    place(panel, (1, 1), (-40, -184), (560, 174), (1, 1))
    panel.set_render_opacity(0)
    def hint_child(widget, pos, size):
        widget.remove_from_parent()
        slot = panel.add_child_to_canvas(widget)
        slot.set_position(unreal.Vector2D(*pos))
        slot.set_size(unreal.Vector2D(*size))
    backdrop = icon('HintBackdrop', '/Game/UI/Textures/T_UI_HintPanel', (0,0), (0,0), (560,174), unreal.LinearColor(1,1,1,1))
    hint_child(backdrop, (0,0), (560,174))
    diamond = icon('HintDiamond','/Game/UI/Textures/T_UI_HintDiamond',(0,0),(0,0),(46,46),unreal.LinearColor(1,1,1,1))
    hint_child(diamond, (505,-19), (46,46))
    title = text('PromptTitleText','FIRST STEPS   /   1 OF 3',20,(0,0),(0,0),(480,38),GOLD,True,110)
    hint_child(title,(34,18),(480,38))
    keys = text('PromptKeyText','W A S D  /  LEFT STICK',16,(0,0),(0,0),(490,30),IVORY,True,60)
    hint_child(keys,(34,63),(490,30))
    prompt = text("PromptText", "Roll along the forest path.", 19, (0,0), (0,0), (480,66))
    hint_child(prompt,(34,100),(480,66))
    prompt.set_editor_property("auto_wrap_text", True)
    prompt.set_render_opacity(0.0)
    notice = make(unreal.CanvasPanel,'NoticePanel')
    place(notice,(0,1),(46,-220),(540,50))
    notice.set_render_opacity(0)
    label = text('NoticeText','+1 LIFE NOTE   /   The forest stirs',18,(0,0),(0,0),(500,35),IVORY)
    label.remove_from_parent()
    slot=notice.add_child_to_canvas(label)
    slot.set_position(unreal.Vector2D(26,8));slot.set_size(unreal.Vector2D(500,35))
    mark=make(unreal.Image,'NoticeDiamond');mark.set_color_and_opacity(GOLD)
    mark.set_render_transform_angle(45)
    slot=notice.add_child_to_canvas(mark)
    slot.set_position(unreal.Vector2D(2,19));slot.set_size(unreal.Vector2D(9,9))
    for name in bound_names:
        widgets[name].set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    print("Saved wilderness HUD with all seven native data bindings.")


if __name__ == "__main__":
    build()
