// Last Seed - music that grows back with the world.
//
// Purpose: starts every stem together at near-zero volume so they stay in sync, then fades one in at each
// restoration milestone. Stem 0 fades in at the start, and stems 1 to 4 at 25, 50, 75 and 100 percent. When
// the level is complete it crossfades to the finale track.
// Design pattern: observer. It listens to URestorationSubsystem and ALSGameMode, and neither knows music exists.
// Connections: lives on AMusicManager. Plays nothing by itself until stems are assigned in the level.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AdaptiveMusicComponent.generated.h"

class UAudioComponent;
class USoundBase;

UCLASS(ClassGroup = (Audio), meta = (BlueprintSpawnableComponent))
class ASSIGNMENT1_API UAdaptiveMusicComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** Fades out the stems and fades in the finale track. Fires once. Stems keep playing if no track is assigned. */
	UFUNCTION(BlueprintCallable, Category = "Music")
	void PlayFinale();

protected:
	virtual void BeginPlay() override;

	/** Looping tracks of equal length, in this order: pads, percussion, bass, melody, strings. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TArray<TObjectPtr<USoundBase>> Stems;

	/** Replaces the stems when the level is complete. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Music")
	TObjectPtr<USoundBase> FinaleTrack;

	/** Volume of a stem that has faded in, where 1 is the sound's own volume. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float StemVolume = 1.f;

	/** Volume of a stem that is waiting for its milestone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.001"))
	float WaitingVolume = 0.001f;

	/** Seconds a stem takes to fade in. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float StemFadeTime = 4.f;

	/** Seconds the crossfade to the finale track takes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float FinaleFadeTime = 3.f;

private:
	UFUNCTION()
	void HandleMilestoneReached(int32 MilestoneIndex);

	void FadeInStem(int32 StemIndex);

	/** The playing stems, kept so they can be faded. Same order as Stems, and an entry is null if that stem has no sound. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAudioComponent>> StemAudio;

	/** The playing finale. Set once the finale has started. */
	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> FinaleAudio;
};
