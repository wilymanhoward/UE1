// Last Seed - turns the restoration value into what the player sees.
//
// Purpose: smoothly moves the material parameter collection, a post-process volume and the height fog from
// the grey Withering look back to the level's own post-process look. Place one in each level.
// A subsystem can't hold editor-assigned assets or level references, which is why this is a separate actor.
// Design pattern: observer. It reads and listens to URestorationSubsystem, and the subsystem never knows it exists.
// Connections: reads URestorationSubsystem. Writes to the UMaterialParameterCollection that all world
// materials read, plus the APostProcessVolume and AExponentialHeightFog assigned to it. The volume's own saturation
// would grey the player too, so when WitherPostMaterial exists, that material does the greying and skips the player.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RestorationDriver.generated.h"

class ADirectionalLight;
class AExponentialHeightFog;
class ASkyLight;
class UNiagaraComponent;
class UNiagaraSystem;
class APostProcessVolume;
class AVolumetricCloud;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMaterialParameterCollection;
class URestorationSubsystem;
class USoundBase;
class UAudioComponent;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ARestorationDriver : public AActor
{
	GENERATED_BODY()

public:
	ARestorationDriver();

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

	/** Needs scalars Restoration and LocalBloomRadius, and vector LastNoteLocation. See ASSET_SETUP.md. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;

	/** Graded from grey back to its own settings. Tick Infinite Extent on it so it covers the whole level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	TObjectPtr<APostProcessVolume> PostProcessVolume;

	/** Thins out as the world recovers. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	TObjectPtr<AExponentialHeightFog> HeightFog;

	/** Post-process material with a Saturation parameter that leaves stencil 1 in full colour. If missing, the volume's saturation is used. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	TSoftObjectPtr<UMaterialInterface> WitherPostMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/LastSeed/Materials/M_LS_WitherPost.M_LS_WitherPost")));

	/** How quickly the visuals catch up with the real value. Higher is faster. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float BlendSpeed = 1.5f;

	/** Radius in cm of the colour that spreads from the last collected note. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float NoteBloomRadius = 800.f;

	/** How quickly that radius grows after a note is collected. Higher is faster. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float NoteBloomSpeed = 3.f;

	/** Post-process saturation at restoration 0. 0 is fully grey and 1 is normal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WitheredSaturation = 0.15f;

	/** Saturation multiplied over the volume's own at restoration 1. 1 gives back the level's original look. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestoredSaturation = 1.f;

	/** Post-process contrast at restoration 0. At restoration 1 the volume's own contrast returns. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WitheredContrast = 0.85f;

	/** Colour multiplied over the image at restoration 0. The default is a cold blue. At restoration 1 the volume's own gain returns. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor WitheredTint = FLinearColor(0.85f, 0.9f, 1.f);

	/** Fog density at restoration 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WitheredFogDensity = 0.05f;

	/** Fog density at restoration 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestoredFogDensity = 0.01f;

	/** Optional cloud layer using the EngineSky cloud material's albedo and coverage parameters. */
	UPROPERTY(EditAnywhere, Category = "Weather")
	TObjectPtr<AVolumetricCloud> WeatherClouds;

	UPROPERTY(EditAnywhere, Category = "Weather")
	TObjectPtr<USoundBase> DistantThunder;
	UPROPERTY(EditAnywhere, Category = "Weather")
	TArray<TObjectPtr<UStaticMesh>> LightningMeshes;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Weather")
	TObjectPtr<UStaticMeshComponent> LightningBolt;

	/** Cloud colour at full storm. The clear colour comes back as the world recovers. */
	UPROPERTY(EditAnywhere, Category = "Weather")
	FLinearColor StormCloudAlbedo = FLinearColor(0.20f, 0.23f, 0.27f);

	/** Cloud coverage added at full storm. */
	UPROPERTY(EditAnywhere, Category = "Weather", meta = (ClampMin = "0"))
	float StormCloudCoverage = 0.24f;

	/** Seconds between strikes, picked at random in this range. */
	UPROPERTY(EditAnywhere, Category = "Weather", meta = (ClampMin = "0.5"))
	float LightningIntervalMin = 6.5f;
	UPROPERTY(EditAnywhere, Category = "Weather", meta = (ClampMin = "0.5"))
	float LightningIntervalMax = 10.f;

	/** Most bolts in one strike. Each extra bolt has a 50% chance. */
	UPROPERTY(EditAnywhere, Category = "Weather", meta = (ClampMin = "1", ClampMax = "5"))
	int32 MaxBoltsPerStrike = 1;

	/** Chance that a strike lands close: a big bolt, thunder almost at once, louder and sharper. */
	UPROPERTY(EditAnywhere, Category = "Weather", meta = (ClampMin = "0", ClampMax = "1"))
	float CloseStrikeChance = 0.f;

	/** Darkens and roughens the picture, dims Sun and Sky Light, darkens the fog and runs the rain while the storm lasts.
	 *  Each value fades back to the level's own as the world recovers. Off leaves only the grey and the lightning. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	bool bStormGrade = false;

	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	TObjectPtr<ADirectionalLight> Sun;

	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	TObjectPtr<ASkyLight> SkyLight;

	/** Exposure bias at full storm. Lower is darker; each 1 is a stop. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	float StormExposureBias = 0.3f;

	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float StormVignette = 0.9f;

	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float StormGrain = 0.35f;

	/** Chromatic aberration at the screen edges at full storm. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0", ClampMax = "5"))
	float StormFringe = 1.5f;

	/** Sun and sky light brightness at full storm, as a fraction of the level's own. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float StormSunScale = 0.12f;
	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0", ClampMax = "1"))
	float StormSkyScale = 0.3f;

	/** Fog colour at full storm. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	FLinearColor StormFogColor = FLinearColor(0.01f, 0.012f, 0.018f);

	/** Sun and sky light added at the peak of a lightning flash, so the strike lights the land. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0"))
	float FlashSunIntensity = 10.f;
	UPROPERTY(EditAnywhere, Category = "Weather|Storm", meta = (ClampMin = "0"))
	float FlashSkyIntensity = 1.5f;

	/** Follow the camera while the storm is strong. */
	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	TObjectPtr<UNiagaraSystem> RainEffect;
	UPROPERTY(EditAnywhere, Category = "Weather|Storm")
	TObjectPtr<UNiagaraSystem> StormWindEffect;

private:
	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	void ApplyVisuals();
	void UpdateWeather(float DeltaSeconds);
	void Strike(float Storm);
	void PlayThunder(float Volume, float Pitch);
	/** 1 while the world is withered, fading to 0 by 75% restoration. */
	float GetStorm() const;

	/** The world's restoration rules. Read each frame. */
	UPROPERTY(Transient)
	TObjectPtr<URestorationSubsystem> Restoration;

	/** This level's copy of WitherPostMaterial, updated as the world recovers. Empty if the asset is missing. */
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> WitherPostInstance;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CloudInstance;
	// LightningBolt plus the extra bolts made at BeginPlay, each with its own material instance.
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Bolts;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BoltInstances;
	// Every thunder still playing, so all of them fade when the storm clears.
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAudioComponent>> ThunderAudios;
	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> Rain;
	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> Wind;

	// The volume's own grading, read at BeginPlay, which full restoration gives back.
	FVector4 ClearSaturation = FVector4(1.f, 1.f, 1.f, 1.f);
	FVector4 ClearContrast = FVector4(1.f, 1.f, 1.f, 1.f);
	FVector4 ClearGain = FVector4(1.f, 1.f, 1.f, 1.f);

	// The level's own values, read at BeginPlay, which the storm fades back to.
	FLinearColor ClearCloudAlbedo = FLinearColor::White;
	float ClearCloudCoverage = 0.f;
	float ClearSunIntensity = 0.f;
	float ClearSkyIntensity = 0.f;
	float ClearExposureBias = 0.f;
	float ClearVignette = 0.f;
	float ClearGrain = 0.f;
	float ClearFringe = 0.f;
	FLinearColor ClearFogColor = FLinearColor::Black;

	float TimeToLightning = 4.5f;
	float LightningGlowTime = 0.f;
	int32 ActiveBolts = 0;

	// What is on screen now. It chases the real value, which jumps with each note.
	float DisplayedRestoration = 0.f;
	float CurrentBloomRadius = 0.f;
};
