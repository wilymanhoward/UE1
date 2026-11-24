"""Apply Wildwood's condensed type and open, left-aligned pause layout."""
import unreal

FONT = '/Game/UI/Fonts/F_Wildwood'
IVORY = unreal.LinearColor(.92,.91,.84,1)
GOLD = unreal.LinearColor(.94,.77,.36,1)


def widgets_for(bp):
    return {w.get_name():w for w in unreal.ObjectIterator(unreal.Widget)
            if w.get_outer() and w.get_outer().get_outer()==bp}


def font(widget, size=None, heading=False):
    info=widget.get_editor_property('font')
    info.set_editor_property('font_object',unreal.load_asset(FONT))
    info.set_editor_property('typeface_font_name','Heading' if heading else 'Regular')
    info.set_editor_property('letter_spacing',90 if heading else 0)
    if size: info.set_editor_property('size',size)
    widget.set_font(info)
    widget.set_color_and_opacity(unreal.SlateColor(IVORY))
    widget.set_shadow_offset(unreal.Vector2D(1,2))
    widget.set_shadow_color_and_opacity(unreal.LinearColor(.01,.015,.01,.9))


def button(widget):
    widget.set_editor_property('is_focusable',True)
    style=widget.get_editor_property('widget_style')
    for name in ['normal','hovered','pressed']:
        brush=style.get_editor_property(name)
        brush.set_editor_property('resource_object',unreal.load_asset('/Game/UI/Textures/T_UI_FocusRule'))
        brush.set_editor_property('draw_as',unreal.SlateBrushDrawType.IMAGE)
        brush.set_editor_property('tint_color',unreal.SlateColor(unreal.LinearColor(1,1,1,1)))
        style.set_editor_property(name,brush)
    style.set_editor_property('normal_padding',unreal.Margin(0,3,0,5))
    style.set_editor_property('pressed_padding',unreal.Margin(0,4,0,4))
    widget.set_style(style)
    child=widget.get_content()
    child.slot.set_padding(unreal.Margin(0))
    child.slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_LEFT)
    if isinstance(child,unreal.TextBlock): font(child,28,True)


def menu_image(widget, name, width=None):
    texture = unreal.load_asset('/Game/UI/Textures/' + name)
    native_width, native_height = texture.blueprint_get_size_x(), texture.blueprint_get_size_y()
    width = width or native_width
    widget.set_brush_from_texture(texture, False)
    brush = widget.get_editor_property('brush')
    size = brush.get_editor_property('image_size')
    size.set_editor_properties({'x': width, 'y': width * native_height / native_width})
    brush.set_editor_property('image_size', size)
    widget.set_brush(brush)


def style_title_menu():
    bp = unreal.load_asset('/Game/UI/WBP_MainMenu')
    w = widgets_for(bp)
    root = w['Root']
    bp.modify()
    backdrop, shade = w['Backdrop'], w['Shade']
    forest, logo_frame = w['ForestCover'], w['TitleArt']
    logo = w['TitleDivider']
    panels = [w[name] for name in ('MainPanel', 'LevelSelectPanel', 'ControlsPanel')]
    slots = [panel.slot for panel in panels]
    panel_layouts = [(s.get_editor_property('horizontal_alignment'), s.get_editor_property('vertical_alignment'),
                      s.get_editor_property('padding')) for s in slots]
    root.clear_children()
    root.set_clipping(unreal.WidgetClipping.CLIP_TO_BOUNDS)
    forest.clear_children()
    forest.set_stretch(unreal.Stretch.SCALE_TO_FILL)
    menu_image(backdrop, 'T_UI_MenuBackdrop')
    forest.add_child(backdrop)
    fill = root.add_child_to_overlay(forest)
    fill.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    fill.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    fill = root.add_child_to_overlay(shade)
    fill.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    fill.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    shade.set_render_opacity(0.28)

    logo_frame.clear_children()
    logo_frame.set_stretch(unreal.Stretch.SCALE_TO_FIT)
    logo_frame.set_stretch_direction(unreal.StretchDirection.DOWN_ONLY)
    menu_image(logo, 'T_UI_LastSeedLogo', 860)
    logo.set_color_and_opacity(unreal.LinearColor(1, 1, 1, 1))
    logo_frame.add_child(logo)
    art = root.add_child_to_overlay(logo_frame)
    art.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
    art.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
    art.set_padding(unreal.Margin(130, 0, 54, 220))
    logo_frame.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)

    for panel, (horizontal, vertical, padding) in zip(panels, panel_layouts):
        slot = root.add_child_to_overlay(panel)
        slot.set_horizontal_alignment(horizontal)
        slot.set_vertical_alignment(vertical)
        slot.set_padding(padding)

    main = w['MainPanel']
    main.slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_LEFT)
    main.slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_BOTTOM)
    main.slot.set_padding(unreal.Margin(90, 0, 24, 92))
    for name in ('GameTitle', 'Tagline'):
        w[name].set_visibility(unreal.SlateVisibility.COLLAPSED)
    for name in ('Play', 'LevelSelect', 'Controls', 'Quit'):
        button(w[name + 'Button'])
        w[name + 'Size'].set_width_override(315)
        w[name + 'Size'].set_height_override(44)
        label = w[name + 'Label']
        font(label, 28, True)
        label.set_editor_property('justification', unreal.TextJustify.LEFT)
        label.slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_TOP)
        label.slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
        label.slot.set_padding(unreal.Margin(12, 0, 0, 0))
        w[name + 'Button'].slot.set_padding(unreal.Margin(0, 0, 0, 5))
    w['PlayLabel'].set_text('PLAY')
    w['Level1Name'].set_text('I  ·  WILDWOOD')
    w['Level2Name'].set_text('II  ·  EMBERWOOD')
    w['PetalTotal'].slot.set_padding(unreal.Margin(0, 17, 0, 0))
    font(w['TotalPetalsText'], 16)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)


def build():
    for name in ['WBP_PauseMenu','WBP_Controls','WBP_MainMenu','WBP_Results','WBP_StoryCard']:
        bp=unreal.load_asset('/Game/UI/'+name)
        if not bp: continue
        for w in widgets_for(bp).values():
            if isinstance(w,unreal.TextBlock):
                font(w,heading=any(t in w.get_name().lower() for t in ['title','heading','label','formname']))
        unreal.EditorAssetLibrary.save_loaded_asset(bp,False)

    bp=unreal.load_asset('/Game/UI/WBP_PauseMenu')
    w=widgets_for(bp)
    w['Panel'].set_brush_color(unreal.LinearColor(0,0,0,0))
    brush=w['Panel'].get_editor_property('background')
    brush.set_editor_property('draw_as',unreal.SlateBrushDrawType.NO_DRAW_TYPE)
    w['Panel'].set_editor_property('background',brush)
    w['Panel'].set_padding(unreal.Margin(0))
    brush=w['Dim'].get_editor_property('background')
    brush.set_editor_property('resource_object',unreal.load_asset('/Game/UI/Textures/T_UI_PauseShade'))
    brush.set_editor_property('draw_as',unreal.SlateBrushDrawType.IMAGE)
    w['Dim'].set_editor_property('background',brush)
    w['Dim'].set_brush_color(unreal.LinearColor(1,1,1,1))
    w['MainPanel'].set_width_override(660)
    w['MainPanel'].clear_height_override()
    slot=w['MainPanel'].slot
    slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_LEFT)
    slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_BOTTOM)
    slot.set_padding(unreal.Margin(90,0,0,75))
    w['Title'].set_text('THE LAST SEED   /   PAUSED')
    font(w['Title'],16,True)
    w['Title'].set_color_and_opacity(unreal.SlateColor(GOLD))
    for name in ['ResumeButton','RestartButton','ControlsButton','MainMenuButton']:
        button(w[name])
        w[name].slot.set_padding(unreal.Margin(0,0,0,3))
    w['MainMenuLabel'].set_text('RETURN TO TITLE SCREEN')
    column=w['Column']
    order=['Title','ResumeButton','RestartButton','ControlsButton','MainMenuButton','Divider','MusicRow','SfxRow']
    for child in list(column.get_all_children()): column.remove_child(child)
    for name in order:
        slot=column.add_child_to_vertical_box(w[name])
        slot.set_padding(unreal.Margin(0,3,0,3))
        slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    w['Title'].slot.set_padding(unreal.Margin(0,0,0,22))
    w['Divider'].set_visibility(unreal.SlateVisibility.COLLAPSED)
    w['MusicRow'].slot.set_padding(unreal.Margin(0,28,150,8))
    w['SfxRow'].slot.set_padding(unreal.Margin(0,0,150,0))
    for name in ['MusicLabel','SfxLabel']:
        font(w[name],18)
    for name in ['MusicSlider','SfxSlider']:
        w[name].set_slider_bar_color(unreal.LinearColor(.25,.26,.22,.75))
        w[name].set_slider_handle_color(GOLD)
    for name in ['MusicIcon','SfxIcon']: w[name].set_visibility(unreal.SlateVisibility.COLLAPSED)
    w['ControlsPanel'].slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    w['ControlsPanel'].slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)

    bp=unreal.load_asset('/Game/UI/WBP_Controls')
    w=widgets_for(bp)
    w['PanelSize'].set_width_override(880)
    w['PanelSize'].clear_height_override()
    w['PanelSize'].slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
    w['PanelSize'].slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
    w['Panel'].set_brush_color(unreal.LinearColor(.025,.035,.025,.94))
    brush=w['Panel'].get_editor_property('background')
    brush.set_editor_property('draw_as',unreal.SlateBrushDrawType.IMAGE)
    brush.set_editor_property('resource_object',None)
    w['Panel'].set_editor_property('background',brush)
    w['Panel'].set_padding(unreal.Margin(45,35,45,30))
    font(w['Title'],34,True)
    w['Title'].set_color_and_opacity(unreal.SlateColor(GOLD))
    font(w['ControlsText'],21)
    for name in ['Title','ControlsText']:
        w[name].set_editor_property('justification',unreal.TextJustify.LEFT)
        w[name].slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    w['ControlsText'].set_text('W A S D / LEFT STICK     Roll\n\nMOUSE / RIGHT STICK     Look around\n\nSPACE / A     Jump\n\nESC / START     Pause')
    w['ControlsText'].set_editor_property('auto_wrap_text',True)
    button(w['BackButton'])
    font(w['BackLabel'],24,True)
    w['BackLabel'].set_text('BACK')
    w['BackButton'].slot.set_padding(unreal.Margin(0,24,0,0))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    style_title_menu()
    print('Saved new font across UI, pause layout and progression-aware controls presentation.')


if __name__=='__main__': build()

