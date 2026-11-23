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
class UMaterialInterface;
class UNiagaraComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UNiagaraSystem;
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

	/** Complete only when Seed lands from a jump inside this volume. */
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

	/**
	 * Emberwood's ending. The goal opens only once every energy (the level's Life Notes) is collected. After the Travel
	 * Shots, Seed shakes harder and harder, bursts, and Next Level opens fully restored.
	 */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	bool bEnergyFinale = false;

	/** Shown when Seed reaches the goal too early. {0} is the energy collected, {1} the total. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	FText MissingEnergyMessage = NSLOCTEXT("LastSeed", "MissingEnergy", "The energy is not full yet ({0}/{1}). Find the rest.");

	/** Seconds Seed shakes before it bursts. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale", meta = (ClampMin = "0.1"))
	float ChargeTime = 3.f;

	/** How far Seed shakes, in cm, just before it bursts. It builds up from nothing. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale", meta = (ClampMin = "0"))
	float ChargeShake = 18.f;

	/** Gathers round Seed while it charges, and grows. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<UNiagaraSystem> ChargeEffect;

	/** The burst, at Seed, scaled by Burst Scale. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<UNiagaraSystem> BurstEffect;

	UPROPERTY(EditAnywhere, Category = "Energy Finale", meta = (ClampMin = "0"))
	float BurstScale = 6.f;

	/** A glowing shell that swells round Seed while it charges, so the gathered energy is plain to see. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<UStaticMesh> ChargeShellMesh;

	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<UMaterialInterface> ChargeShellMaterial;

	/** The shell's diameter in cm just before the burst. It grows from a tenth of this. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale", meta = (ClampMin = "0"))
	float ChargeShellSize = 450.f;

	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<USoundBase> ChargeSound;

	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<USoundBase> BurstSound;

	/** The witch's reaction, heard over the burst and through the white flash. */
	UPROPERTY(EditAnywhere, Category = "Energy Finale")
	TObjectPtr<USoundBase> BurstVoice;

	/** Holds Seed still and plays the charge and burst. OnFinished runs once the screen is white. */
	void PlayEnergyBurst(ASeedBall* Ball, TFunction<void()> OnFinished);

protected:
	virtual void BeginPlay() override;

private:
	void UpdateEnergyBurst(float DeltaSeconds);
	void SpawnBurstLightning(const FVector& Centre);

	UPROPERTY()
	TObjectPtr<UStaticMesh> BurstLightningMesh;

	UPROPERTY()
	TObjectPtr<USoundBase> ElectricBlastSound;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> ChargeComponent;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> ChargeShell;

	TWeakObjectPtr<ASeedBall> BurstBall;
	TFunction<void()> OnBurstFinished;
	FVector BurstAnchor = FVector::ZeroVector;
	// Seconds since the charge began, or below zero when no burst is playing.
	float BurstTime = -1.f;
	bool bBurst = false;
	float LastWarningTime = -100.f;
};
