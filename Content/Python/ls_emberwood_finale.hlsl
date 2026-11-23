float t = max(0.0, ShotTime);
float3 paint = Texture2DSample(FrameTex, FrameTexSampler, UV).rgb;
float3 gray = dot(paint, float3(0.2126, 0.7152, 0.0722)).xxx;

if (Surge > 1.5) {
    float2 fromSeed = (UV - float2(0.711, 0.829)) * float2(1.78, 1.0);
    float energy = exp(-dot(fromSeed, fromSeed) * 29.0);
    float build = smoothstep(0.4, 4.6, t);
    float pulse = 0.50 + 0.50 * sin(t * (7.0 + 2.0 * build));
    float lava = smoothstep(0.72, 0.8, UV.x) * smoothstep(0.06, 0.52, paint.r - paint.b);
    paint *= 1.0 + 0.10 * lava * sin(UV.y * 33.0 - 6.0 * t);
    return saturate(paint + float3(0.09, 0.38, 0.15) * energy * build * pulse);
}

if (Surge < 0.5) {
    float fall = pow(saturate(t / 1.04), 1.7);
    float bury = smoothstep(0.96, 1.56, t);
    float2 seedCenter = float2(lerp(0.474, 0.53, fall), 0.37 + 0.29 * fall + 0.22 * bury);
    float2 seedUV = (UV - seedCenter) / float2(0.147, 0.240) + 0.5;
    float4 seed = Texture2DSample(SeedTex, SeedTexSampler, saturate(seedUV));
    float visible = step(0.0, min(seedUV.x, seedUV.y)) * step(max(seedUV.x, seedUV.y), 1.0);
    float soil = 0.756 + 0.002 * sin(324.0 * UV.x);
    visible *= 1.0 - smoothstep(soil - 0.001, soil + 0.001, UV.y);
    float2 radius = (UV - float2(0.53, 0.756)) * float2(1.78, 1.0);
    float light = exp(-dot(radius, radius) * 240.0) * smoothstep(1.48, 2.72, t);
    paint = lerp(gray * 0.78, paint, light);
    paint = lerp(paint, seed.rgb, seed.a * visible);
    paint += float3(0.22, 0.49, 0.13) * light;
    return lerp(saturate(paint), float3(0.89, 0.98, 0.79), smoothstep(2.86, 3.18, t));
}

float2 root = float2(0.53, 0.78);
float growth = lerp(0.045, 1.0, smoothstep(0.55, 4.2, t));
float2 treeSize = float2(0.434, 0.73) * growth;
float2 treeUV = (UV - root) / treeSize + float2(0.5, 0.966);
float4 tree = Texture2DSample(TreeTex, TreeTexSampler, saturate(treeUV));
float inTree = step(0.0, min(treeUV.x, treeUV.y)) * step(max(treeUV.x, treeUV.y), 1.0);
float2 shadeUV = (UV - root) / (float2(0.17, 0.027) * growth);
paint *= 1.0 - 0.28 * exp(-dot(shadeUV, shadeUV)) * growth;
paint = lerp(paint, tree.rgb, tree.a * inTree * smoothstep(0.38, 0.95, t));

float distanceFromRoots = length((UV - root) * float2(1.47, 1.0));
float colorFront = lerp(-0.12, 1.25, smoothstep(1.2, 5.1, t));
float restored = 1.0 - smoothstep(colorFront - 0.03, colorFront + 0.15, distanceFromRoots);
float glowDistance = (distanceFromRoots - colorFront) / 0.11;
float glow = exp(-glowDistance * glowDistance);
glow *= smoothstep(1.2, 2.0, t) * (1.0 - smoothstep(4.4, 5.25, t));
gray = dot(paint, float3(0.2126, 0.7152, 0.0722)).xxx;
float3 scene = lerp(gray * 0.76, paint, restored);
scene += float3(0.12, 0.28, 0.075) * glow;
return lerp(float3(0.89, 0.98, 0.79), saturate(scene), smoothstep(0.0, 0.55, t));
