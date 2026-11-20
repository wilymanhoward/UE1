// Last Seed - the opening cutscene: illustrated shots, motion, captions and audio.
//
// Purpose: plays full-screen shots with optional UI materials for motion and a separate narration track.
// The final picture dissolves into a matched seed close-up, then the camera and bars ease into gameplay.
// It builds its own widgets in code, so it needs no Widget Blueprint.
// Design pattern: observer. OnFinished tells the controller the cutscene is over.
// Connections: created by ALSPlayerController::PlayIntro, from the shots and music on an AStoryTrigger. The level
// build fills those from Content/Python/ls_intro_shots.py.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSIntroWidget.generated.h"

class UAudioComponent;
class ACameraActor;
class UButton;
class UImage;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class USoundBase;
class UTextBlock;
class UOverlay;
class USizeBox;
class UTexture2D;

enum class ELSIntroTransition : uint8
{
	Gameplay,
	Opening,
	Travel,
	Arrival
};

USTRUCT(BlueprintType)
struct FLSIntroShot
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	TObjectPtr<UTexture2D> Image;

	/** Optional UI material. The widget supplies FrameTex and the local playback time. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	TObjectPtr<UMaterialInterface> MotionMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (ClampMin = "0.1"))
	float Duration = 4.f;

	/** How far in the picture is zoomed at the start and end of the shot. 1 fills the screen exactly. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (ClampMin = "1"))
	float StartZoom = 1.05f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (ClampMin = "1"))
	float EndZoom = 1.15f;

	/** Where the picture is shifted, as a fraction of the screen, at the start and end. Kept within the zoom's margin. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	FVector2D StartPan = FVector2D::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	FVector2D EndPan = FVector2D::ZeroVector;

	/** Seconds this shot takes to fade in over the one before. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (ClampMin = "0"))
	float FadeIn = 1.f;

	/** Starts from a white flash. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	bool bFlash = false;

	/** Optional seed centre (X/Y) and height (Z) as fractions of the final frame. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	FVector SeedMatch = FVector::ZeroVector;

	/** Shown at the bottom of the screen. A caption the same as the shot before stays up without fading. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (MultiLine = "true"))
	FText Caption;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnIntroFinished);

UCLASS()
class ASSIGNMENT1_API ULSIntroWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Sets what to play. Call before adding it to the viewport. Shots must not be empty. */
	void SetIntro(const TArray<FLSIntroShot>& InShots, USoundBase* InMusic, USoundBase* InVoiceOver,
		ELSIntroTransition InTransition, const FVector& InRevealTarget);

	/** Fires once, when the cutscene ends or is skipped. */
	UPROPERTY(BlueprintAssignable, Category = "Intro")
	FOnIntroFinished OnFinished;

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	UFUNCTION()
	void Finish();

	UFUNCTION()
	void RequestSkip();
	void MatchSeedCamera(const FVector2D& ViewportSize);
	void RestoreCamera();
	bool MatchesSeed() const { return Transition == ELSIntroTransition::Opening || Transition == ELSIntroTransition::Arrival; }

	/** Places a shot's picture for local time Seconds into the shot. */
	void ApplyShot(UImage* Image, const FLSIntroShot& Shot, float Seconds) const;

	float ShotStart(int32 Index) const;

	UPROPERTY(Transient)
	TObjectPtr<UImage> BackImage;

	UPROPERTY(Transient)
	TObjectPtr<UOverlay> PictureLayer;
	UPROPERTY(Transient)
	TObjectPtr<UImage> TransitionVeil;
	UPROPERTY(Transient)
	TObjectPtr<USizeBox> TopBar;
	UPROPERTY(Transient)
	TObjectPtr<USizeBox> BottomBar;
	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> HandoffCamera;
	UPROPERTY(Transient)
	TObjectPtr<AActor> GameplayViewTarget;

	FVector GameplayCameraLocation = FVector::ZeroVector;
	FVector MatchedCameraLocation = FVector::ZeroVector;
	FRotator GameplayCameraRotation = FRotator::ZeroRotator;
	FVector RevealTarget = FVector::ZeroVector;
	ELSIntroTransition Transition = ELSIntroTransition::Opening;

	UPROPERTY(Transient)
	TObjectPtr<UImage> FrontImage;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ActiveMotion;

	UPROPERTY(Transient)
	TObjectPtr<UImage> Flash;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> CaptionText;

	UPROPERTY(Transient)
	TObjectPtr<UButton> SkipButton;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> MusicAudio;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> Music;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> VoiceOver;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> VoiceOverAudio;

	TArray<FLSIntroShot> Shots;
	double PlaybackStartTime = 0.0;
	float TotalTime = 0.f;
	int32 CurrentShot = -1;
	bool bFinished = false;
	bool bMatchingStarted = false;
	double SkipStartTime = -1.0;
	float SkipPictureOpacity = 1.f;
	float SkipVeilOpacity = 0.f;
	float SkipBarTranslation = 0.f;
	FVector SkipCameraLocation = FVector::ZeroVector;
	FRotator SkipCameraRotation = FRotator::ZeroRotator;
};
