// Last Seed - tells a piece of the story.
//
// Purpose: when the ball enters, or as soon as the level starts, it plays a level sequence if one is assigned, or
// otherwise shows a set of story text cards. It plays once. Gameplay input is off while it runs.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. ALSPlayerController::PlayStory does the work.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "StoryTrigger.generated.h"

class ULevelSequence;

UCLASS()
class ASSIGNMENT1_API AStoryTrigger : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AStoryTrigger();

	virtual void OnBallOverlap(ASeedBall* Ball) override;

protected:
	virtual void BeginPlay() override;

	/** Plays a cutscene. If this is set, Cards are ignored. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TObjectPtr<ULevelSequence> Sequence;

	/** Story text, one card per entry. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story", meta = (MultiLine = "true"))
	TArray<FText> Cards;

	/** Plays as soon as the level starts, wherever the ball is. Use this for an opening cutscene. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	bool bPlayOnStart = false;

private:
	void Play();

	bool bPlayed = false;
};
