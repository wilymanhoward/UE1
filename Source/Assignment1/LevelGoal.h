// Last Seed - the end of a level, and that level's settings.
//
// Purpose: completes the level when the ball enters. A game mode Blueprint is shared by every level, so values
// that differ per level, such as par time and the next level, are set here on the placed actor.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. Calls ALSGameMode::CompleteLevel, which reads these values.

#pragma once

#include "CoreMinimal.h"
#include "LSIntroWidget.h"
#include "LSVolumeBase.h"
#include "LevelGoal.generated.h"

class ULevelSequence;
class UWorld;

UCLASS()
class ASSIGNMENT1_API ALevelGoal : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	ALevelGoal();

	virtual void OnBallOverlap(ASeedBall* Ball) override;
	virtual void Tick(float DeltaSeconds) override;

	/** Plays before the results. Leave empty to use Ending Cards. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal")
	TObjectPtr<ULevelSequence> EndingSequence;

	/** Story text shown before the results if there is no Ending Sequence. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal", meta = (MultiLine = "true"))
	TArray<FText> EndingCards;

	/** When a destination is assigned, these shots replace the results screen and lead into that level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal")
	TArray<FLSIntroShot> TravelShots;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal")
	TObjectPtr<USoundBase> TravelAudio;

	/** Complete only while the ball is rising from a jump inside this volume. */
	UPROPERTY(EditAnywhere, Category = "Level Goal")
	bool bRequireJump = false;

	/** Opened by the results screen's Next button. Leave empty on the last level. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal")
	TSoftObjectPtr<UWorld> NextLevel;

	/** Shown after the results when there is no Next Level, before returning to the main menu. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Goal", meta = (MultiLine = "true"))
	TArray<FText> CreditsCards;

	/** Seconds to beat for the third star. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ParTimeSeconds = 300.f;

	/** Golden Petals needed for the third star. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	int32 RequiredPetals = 2;

protected:
	virtual void BeginPlay() override;
};
