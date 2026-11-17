// Last Seed - turns the restoration value into what the player sees.
//
// Purpose: smoothly moves the material parameter collection, a post-process volume and the height fog from
// the grey Withering look to the warm restored look. Place one in each level.
// A subsystem can't hold editor-assigned assets or level references, which is why this is a separate actor.
// Design pattern: observer. It reads and listens to URestorationSubsystem, and the subsystem never knows it exists.
// Connections: reads URestorationSubsystem. Writes to the UMaterialParameterCollection that all world
// materials read, plus the APostProcessVolume and AExponentialHeightFog assigned to it. The volume's own saturation
// would grey the player too, so when WitherPostMaterial exists, that material does the greying and skips the player.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RestorationDriver.generated.h"

class AExponentialHeightFog;
class APostProcessVolume;
class AVolumetricCloud;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMaterialParameterCollection;
class URestorationSubsystem;
class USoundBase;

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

	/** Graded from grey to warm. Tick Infinite Extent on it so it covers the whole level. */
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

	/** Post-process saturation at restoration 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestoredSaturation = 1.1f;

	/** Post-process contrast at restoration 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WitheredContrast = 0.85f;

	/** Post-process contrast at restoration 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestoredContrast = 1.05f;

	/** Colour multiplied over the image at restoration 0. The default is a cold blue. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor WitheredTint = FLinearColor(0.85f, 0.9f, 1.f);

	/** Colour multiplied over the image at restoration 1. The default is a warm gold. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FLinearColor RestoredTint = FLinearColor(1.08f, 1.f, 0.9f);

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

private:
	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	void ApplyVisuals();
	void UpdateWeather(float DeltaSeconds);
	void PlayDistantThunder();

	/** The world's restoration rules. Read each frame. */
	UPROPERTY(Transient)
	TObjectPtr<URestorationSubsystem> Restoration;

	/** This level's copy of WitherPostMaterial, updated as the world recovers. Empty if the asset is missing. */
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> WitherPostInstance;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CloudInstance;

	FLinearColor ClearCloudAlbedo = FLinearColor::White;
	float ClearCloudCoverage = 0.f;
	float TimeToLightning = 4.5f;
	float LightningGlowTime = 0.f;
	FTimerHandle ThunderTimer;

	// What is on screen now. It chases the real value, which jumps with each note.
	float DisplayedRestoration = 0.f;
	float CurrentBloomRadius = 0.f;
};
