// All coordinates refer to the original 1920x1080 paintings.
// Cue and ShotTime are uniform for each full-screen draw.
float t = ShotTime;
float2 uv = UV;
float3 amber = float3(1.0, 0.51, 0.09);
float3 col;
float span = 16.0 / 9.0;

if (Cue < 2.5) {
    bool heartTree = Cue > 1.5;
    float shade = smoothstep(4.1, 5.0, t);
    float2 treeUV = (uv - 0.5) * lerp(0.975, 0.943, smoothstep(0.0, 5.0, t)) + 0.5;
    float3 tree = Texture2DSample(FrameTex, FrameTexSampler, treeUV).rgb
                  * lerp(float3(1.0, 1.0, 1.0), float3(0.38, 0.47, 0.64), shade);
    if (heartTree && t >= 0.74) {
        return tree;
    }

    float forestTime = t + (heartTree ? 4.0 : 0.0);
    float depth = saturate(abs(uv.x - 0.5) * 1.2 + max(uv.y - 0.45, 0.0));
    float drift = (smoothstep(0.0, 4.74, forestTime) - 0.5) * (0.012 + 0.04 * depth);
    float2 forestUV = (uv - 0.5) * lerp(0.975, 0.930, smoothstep(0.0, 4.74, forestTime)) + 0.5
                      + float2(drift, 0.0);
    col = Texture2DSample(LayerTex, LayerTexSampler, forestUV).rgb;

    // Reuse the two painted leaves. Their tilt and fall speed vary with depth.
    [unroll]
    for (int i = 0; i < 3; ++i) {
        float age = max(0.0, forestTime - (i == 2 ? 1.3 : 0.0));
        float2 center = i == 0 ? float2(0.334, 0.470) :
                        i == 1 ? float2(0.612, 0.630) : float2(0.68, 0.26);
        center += float2((i == 1 ? -0.026 : 0.034) * age + 0.023 * sin(age * 3.2 + i), 0.095 * age + 0.017 * age * age);
        float2 p = (uv - center) * float2(1920.0, 1080.0);
        float tilt = 0.47 * sin(age * 3.7 + i * 1.8) + age * (i == 1 ? -0.37 : 0.30);
        p = mul(float2x2(cos(tilt), sin(tilt), -sin(tilt), cos(tilt)), p);
        p /= float2(1.0, 0.70 + 0.30 * cos(age * 5.1 + i)) * (i == 2 ? 0.52 : 1.0);
        float2 size = i == 1 ? float2(126.0, 105.0) : float2(158.0, 120.0);
        float2 spriteUV = p + size * 0.5;
        if (all(spriteUV >= 0.0) && all(spriteUV < size)) {
            float4 leaf = Texture2DSampleLevel(SeedTex, SeedTexSampler, (spriteUV + float2(i == 1 ? 170.0 : 0.0, 0.0)) / float2(512.0, 128.0), 0);
            float reveal = i == 2 ? smoothstep(1.3, 1.62, forestTime) : 1.0;
            col = lerp(col, leaf.rgb, leaf.a * reveal);
        }
    }

    [unroll]
    for (int j = 0; j < 3; ++j) {
        float age = max(forestTime - j * 0.30, 0.0);
        float2 center = float2(0.55 - 0.019 * j + (0.047 - 0.004 * j) * age,
                               0.279 + 0.014 * j - 0.028 * age + 0.013 * sin(2.4 * age + j));
        float2 p = (uv - center) * float2(1920.0, 1080.0) / (0.94 - 0.16 * j);
        p.y -= 10.0 * smoothstep(3.0, 31.0, abs(p.x)) * sin(age * 15.0 + j * 1.6);
        float2 spriteUV = p + float2(42.5, 25.0);
        if (all(spriteUV >= 0.0) && all(spriteUV < float2(85.0, 50.0))) {
            float4 bird = Texture2DSampleLevel(SeedTex, SeedTexSampler, (spriteUV + float2(310.0, 0.0)) / float2(512.0, 128.0), 0);
            float visibility = (j == 0 ? 1.0 : smoothstep(0.0, 0.22, age)) * (1.0 - smoothstep(1.35 + j * 0.26, 2.27 + j * 0.31, age));
            col = lerp(col, bird.rgb, bird.a * visibility);
        }
    }

    if (!heartTree) {
        return col;
    }
    // Light from the clearing carries the cut as the camera keeps moving forward.
    float mix = smoothstep(0.0, 0.74, t);
    float2 sun = (uv - lerp(float2(0.59, 0.21), float2(0.55, 0.38), mix)) * float2(span, 1.0);
    float sunGlow = 0.29 * sin(3.141593 * mix) * exp(-dot(sun, sun) * 7.2);
    return lerp(lerp(col, tree, mix), float3(1.0, 0.89, 0.62), sunGlow);
}

if (Cue < 3.5) {
    col = Texture2DSample(FrameTex, FrameTexSampler, uv).rgb;
    if (all(uv > float2(0.28, 0.25)) && all(uv < float2(0.42, 0.46))) {
        // Key the painted mint wisp against the blue sky and hold its tip by the fingers.
        float sway = 0.012 * (1.0 - smoothstep(0.27, 0.46, uv.y)) * sin(t * 3.6 + (uv.y - 0.27) * 27.0);
        float3 shifted = Texture2DSample(FrameTex, FrameTexSampler, uv - float2(sway, 0.0)).rgb;
        float wisp = smoothstep(-0.235, -0.13, max(col.g - col.b, shifted.g - shifted.b));
        col = lerp(col, shifted, wisp);
    }
    if (t < 0.82) {
        // Match the shadow at the end of the Heart Tree shot before revealing the witch.
        float3 old = Texture2DSample(OtherTex, OtherTexSampler, (uv - 0.5) * 0.943 + 0.5).rgb;
        float3 shadow = float3(0.38, 0.47, 0.64);
        col = lerp(old * shadow, col * lerp(shadow, float3(1.0, 1.0, 1.0), smoothstep(0.24, 0.82, t)),
                   smoothstep(0.0, 0.52, t));
    }
    return col;
}

if (Cue < 4.5) {
    float flare = 0.72 * (1.0 - smoothstep(0.0, 0.29, t));
    float impulse = exp(-14.0 * t) * sin(t * 68.0);
    float2 hitUV = uv + float2(0.004 * impulse, 0.003 * impulse);
    float3 original = Texture2DSample(FrameTex, FrameTexSampler, hitUV).rgb;
    float3 background = Texture2DSample(LayerTex, LayerTexSampler, hitUV).rgb;

    // The curse spreads outward from the witch's hands without changing direction.
    float2 anchor = float2(0.50, 0.43);
    float spread = lerp(1.0, 1.95, smoothstep(0.0, 2.65, t));
    float2 paintUV = anchor + (hitUV - anchor) / spread;
    col = background;
    if (all(paintUV > float2(0.078, 0.061)) && all(paintUV < float2(0.937, 0.705)) &&
        !(paintUV.y > 0.338 && paintUV.x > 0.405 && paintUV.x < 0.603)) {
        float3 paint = Texture2DSampleLevel(FrameTex, FrameTexSampler, paintUV, 0).rgb;
        float3 display = pow(saturate(paint), 1.0 / 2.2);
        float alpha = saturate(min((display.g - display.b - 0.118) / 0.157, (display.g - display.r - 0.255) / 0.255));
        float visibility = 1.0 - smoothstep(1.9, 2.92, t);
        col = lerp(background, paint * (1.0 + 0.19 * exp(-1.5 * t)), alpha * visibility);
    }
    col = lerp(original, col, smoothstep(0.02, 0.24, t));
    return lerp(col, float3(0.79, 1.0, 0.84), flare);
}

if (Cue < 5.5) {
    col = Texture2DSample(FrameTex, FrameTexSampler, uv).rgb;
    float luminance = dot(col, float3(0.2126, 0.7152, 0.0722));
    float canopy = uv.x + 0.14 * (uv.y - 0.5) + 0.045 * sin(8.0 * uv.y);
    float front = lerp(-0.40, 1.38, smoothstep(0.0, 4.3, t));
    float drained = smoothstep(-0.23, 0.23, front - canopy);
    return lerp(col, luminance * float3(0.92, 0.93, 1.03), drained);
}

if (Cue < 6.5) {
    float impact = max(t - 1.88, 0.0);
    float shake = exp(-8.2 * impact) * sin(56.0 * impact);
    float2 sampleUV = (uv - 0.5) * 0.972 + 0.5 + float2(0.009, 0.006) * shake;
    col = Texture2DSample(FrameTex, FrameTexSampler, sampleUV).rgb;
    // Small uneven silhouettes break away from the crown after the crack.
    [unroll]
    for (int i = 0; i < 6; ++i) {
        float k = float(i);
        float age = max(0.0, impact - k * 0.065);
        float2 pos = float2(0.25 + k * 0.092, 0.28 + 0.035 * sin(k * 3.2));
        pos += float2(0.034 * sin(age * 4.0 + k), 0.19 * age + 0.035 * age * age);
        float2 leaf = (uv - pos) * float2(span, 1.0);
        float rotation = k + age * 3.6;
        leaf = mul(float2x2(cos(rotation), -sin(rotation), sin(rotation), cos(rotation)), leaf);
        float shape = 1.0 - smoothstep(0.72, 1.0, length(leaf / float2(0.011, 0.0045)));
        float alpha = smoothstep(0.0, 0.10, age) * (1.0 - smoothstep(1.5, 2.3, age));
        col = lerp(col, float3(0.028, 0.03, 0.047), shape * alpha);
    }
    return col;
}

bool landing = Cue > 7.5;
float approach = landing ? smoothstep(3.3, 5.2, t) : 0.0;
uv = (uv - 0.5) / lerp(1.0, 1.43, approach) + 0.5 + float2(0.021, 0.156) * approach;
col = Texture2DSample(LayerTex, LayerTexSampler, uv).rgb;
float flight = saturate((t - 0.1) / 4.9);
float bounce = sin(3.141593 * saturate((t - 0.14) / 0.50)) * 0.046;
float settle = landing ? (1.0 - smoothstep(0.0, 0.14, t)) * 0.027 + bounce : 0.0;
float2 seedHome = float2(0.524, 0.695);
float2 seedPos = landing ? seedHome - float2(0.0, settle)
                         : float2(lerp(0.485, seedHome.x, flight) + 0.022 * sin(9.0 * flight) * (1.0 - flight),
                                  lerp(0.20, seedHome.y - 0.027, pow(flight, 1.25)));
float seedScale = landing ? 1.0 : lerp(0.72, 1.0, flight);
float2 seedSample = (uv - seedPos) / seedScale + seedHome;
float3 seed = Texture2DSample(SeedTex, SeedTexSampler, saturate(seedSample)).rgb;
float2 seedPixel = seedSample * float2(1920.0, 1080.0);
float key = 0.0;
if (all(seedPixel >= float2(923.0, 658.0)) && all(seedPixel <= float2(1089.0, 834.0))) {
    // Use the painted outline so the amber ground underneath the seed stays in the background.
    const float2 outline[24] = {
        float2(1086, 661), float2(1074, 680), float2(1068, 707), float2(1065, 745),
        float2(1063, 775), float2(1053, 798), float2(1040, 814), float2(1021, 824),
        float2(995, 831), float2(965, 830), float2(950, 827), float2(942, 829),
        float2(940, 822), float2(931, 806), float2(926, 782), float2(927, 762),
        float2(935, 738), float2(948, 721), float2(968, 706), float2(989, 698),
        float2(1012, 693), float2(1037, 688), float2(1057, 681), float2(1074, 668)
    };
    bool insideSeed = false;
    float edgeSquared = 100000.0;
    [unroll]
    for (int j = 0; j < 24; ++j) {
        float2 a = outline[j];
        float2 b = outline[(j + 1) % 24];
        float2 edge = b - a;
        float2 offset = seedPixel - a;
        float2 nearest = offset - edge * saturate(dot(offset, edge) / dot(edge, edge));
        edgeSquared = min(edgeSquared, dot(nearest, nearest));
        if ((a.y > seedPixel.y) != (b.y > seedPixel.y) && seedPixel.x < a.x + edge.x * offset.y / edge.y) {
            insideSeed = !insideSeed;
        }
    }
    key = smoothstep(-1.05, 0.80, (insideSeed ? 1.0 : -1.0) * sqrt(edgeSquared));
}
float2 glow = (uv - seedPos) * float2(span, 1.0);
float2 shadow = (uv - float2(seedPos.x, 0.767)) / float2(0.043, 0.016);
float shadowAlpha = (landing ? 0.48 : lerp(0.02, 0.30, flight)) * exp(-dot(shadow, shadow));
col *= 1.0 - shadowAlpha;
col += amber * (landing ? 0.075 : 0.20) * exp(-length(glow) * 15.0);
col = lerp(col, seed, key);
if (landing) {
    float dustTime = max(0.0, t - 0.14);
    float2 dust = (uv - float2(seedHome.x, 0.769 - dustTime * 0.018)) / float2(1.0, 0.34);
    float dustRadius = length(dust);
    float dustEdge = (1.0 - smoothstep(0.004, 0.013, abs(dustRadius - (0.014 + 0.12 * dustTime))));
    col = lerp(col, float3(0.70, 0.57, 0.36), 0.27 * dustEdge * smoothstep(0.0, 0.045, dustTime) * (1.0 - smoothstep(0.18, 0.70, dustTime)));
    float3 still = Texture2DSample(FrameTex, FrameTexSampler, uv).rgb;
    col = lerp(col, still, smoothstep(0.68, 0.96, t));
}
return col;

