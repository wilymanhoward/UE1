float t = max(ShotTime, 0.0);
float2 uv = UV;
float3 light = 0.0;

if (Surge < 0.5) {
    float fall = pow(saturate(t / 0.83), 1.7);
    float bury = smoothstep(0.80, 1.34, t);
    float2 center = float2(lerp(0.475, 0.532, fall), 0.405 + 0.248 * fall + 0.226 * bury);
    float2 coord = (uv - center) / float2(0.147, 0.240) + 0.5;
    float4 seed = Texture2DSample(SeedTex, SeedTexSampler, saturate(coord));
    float soilLine = 0.755 + 0.002 * sin(uv.x * 324.0);
    float visible = step(0.0, coord.x) * step(coord.x, 1.0) * step(0.0, coord.y) * step(coord.y, 1.0);
    visible *= 1.0 - smoothstep(soilLine - 0.001, soilLine + 0.001, uv.y);

    float3 dirt = Texture2DSample(FrameTex, FrameTexSampler, uv).rgb;
    float shadow = 1.0 - smoothstep(0.36, 1.0, length((uv - float2(0.532, 0.760)) / float2(0.046, 0.012)));
    dirt *= 1.0 - shadow * 0.24 * smoothstep(0.17, 0.78, t) * (1.0 - 0.6 * bury);
    float3 scene = lerp(dirt, seed.rgb, seed.a * visible);

    float kick = max(t - 0.81, 0.0);
    [unroll]
    for (int i = 0; i < 9; ++i) {
        float signX = i % 2 == 0 ? -1.0 : 1.0;
        float drift = 0.055 + 0.014 * i;
        float2 fleck = float2(0.533 + signX * (0.006 + kick * drift),
                            0.756 - kick * (0.12 + 0.018 * i) + 0.32 * kick * kick);
        float size = 0.0023 + 0.0003 * (i % 4);
        float chip = 1.0 - smoothstep(size * 0.68, size, length((uv - fleck) * float2(1.68, 0.9)));
        float active = step(0.81, t) * step(fleck.y, 0.756) * (1.0 - smoothstep(0.19, 0.53, kick));
        scene = lerp(scene, float3(0.24, 0.115, 0.047), chip * active);
    }
    return scene;
}

if (Surge < 1.5) {
    float lean = smoothstep(0.0, 3.45, t);
    uv = lerp(uv, float2(0.47, 0.57), 0.061 * lean);
    float cape = 1.0 - smoothstep(0.08, 0.24, length((uv - float2(0.18, 0.43)) * float2(1.3, 1.0)));
    uv.x += cape * 0.005 * sin(29.0 * uv.y + 3.15 * t);
    float wisp = 1.0 - smoothstep(0.015, 0.072, length((uv - float2(0.559, 0.776)) * float2(1.68, 1.0)));
    float3 ink = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
    float magic = smoothstep(0.06, 0.22, ink.g - max(ink.r, ink.b));
    uv.x += wisp * magic * 0.008 * sin(4.2 * t + uv.y * 43.0);
    light += float3(0.024, 0.14, 0.07) * wisp * magic * smoothstep(1.4, 3.3, t);
} else if (Surge < 2.5) {
    float lift = smoothstep(0.12, 1.44, t);
    float travel = smoothstep(1.36, 3.58, t);
    float rush = smoothstep(2.0, 4.18, t);
    float shake = exp(-5.9 * t);
    uv = lerp(uv, float2(0.789, 0.357), 0.29 * rush);
    uv += shake * float2(0.007 * sin(47.0 * t), 0.005 * sin(59.0 * t));
    float ribbon = (1.0 - smoothstep(0.11, 0.29, abs(uv.x - 0.71)))
                 * (1.0 - smoothstep(0.13, 0.31, abs(uv.y - 0.54)));
    float3 paint = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
    float mint = smoothstep(0.028, 0.27, paint.g - max(paint.r, paint.b)) * ribbon;
    uv.x += mint * 0.0047 * sin(50.0 * uv.y - 7.0 * t);
    paint = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;

    // FrameTex is a clean plate. The transparent sprite is the only seed in this shot.
    float2 center = float2(0.688 + 0.100 * travel, 0.863 - 0.229 * lift - 0.285 * travel);
    float2 size = float2(0.087, 0.150) * (1.0 - 0.57 * travel);
    float2 coord = (uv - center) / size + 0.5;
    float4 seed = Texture2DSample(SeedTex, SeedTexSampler, saturate(coord));
    float visible = step(0.0, coord.x) * step(coord.x, 1.0) * step(0.0, coord.y) * step(coord.y, 1.0);
    visible *= 1.0 - smoothstep(0.752, 0.763, uv.y);
    visible *= 1.0 - smoothstep(0.80, 1.0, travel);
    paint = lerp(paint, seed.rgb, seed.a * visible);
    light = mint * float3(0.035, 0.19, 0.088) * (0.4 + 0.33 * sin(6.0 * t + uv.x * 27.0));
    return saturate(paint * (0.90 + 0.10 * lift) + light);
} else {
    struct SmokeNoise {
        float valueAt(float2 position) {
            float2 cell = floor(position);
            float2 blend = frac(position);
            blend = blend * blend * (3.0 - 2.0 * blend);
            float4 corners = frac(sin(dot(cell, float2(127.1, 311.7)) +
                                      float4(0.0, 127.1, 311.7, 438.8)) * 43758.5453);
            return lerp(lerp(corners.x, corners.y, blend.x), lerp(corners.z, corners.w, blend.x), blend.y);
        }
    };
    SmokeNoise noise;
    float rise = saturate((0.53 - UV.y) / 0.44);
    float2 flow = float2(UV.x * 8.0 - 0.32 * t, UV.y * 11.0 + 0.92 * t);
    float curl = noise.valueAt(flow * 0.55 + float2(0.0, 8.0));
    float billows = 0.72 * noise.valueAt(flow + float2(1.5 * curl, 0.0)) +
                    0.28 * noise.valueAt(flow * 2.1 + float2(3.1, 4.7));
    float plumeCenter = 0.53 + 0.11 * rise + 0.024 * sin(t * 0.9 + rise * 5.0);
    float plumeWidth = lerp(0.085, 0.29, rise);
    float plume = 1.0 - smoothstep(0.0, plumeWidth, abs(UV.x - plumeCenter));
    float corridor = smoothstep(0.23, 0.34, UV.x) * (1.0 - smoothstep(0.64, 0.72, UV.x));
    float air = smoothstep(0.07, 0.21, UV.y) * (1.0 - smoothstep(0.40, 0.51, UV.y));
    float opacity = 0.48 * plume * corridor * air * smoothstep(0.22, 0.72, billows);
    float3 paint = Texture2DSample(FrameTex, FrameTexSampler, UV).rgb;
    float3 smoke = lerp(float3(0.22, 0.049, 0.031), float3(0.91, 0.36, 0.16), 1.0 - rise);
    return lerp(paint, smoke, opacity);
}

return saturate(Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb + light);
