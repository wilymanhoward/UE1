// See LSIntroWidget.h for this class's purpose and connections.

#include "LSIntroWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/Button.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "Engine/Font.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "SceneView.h"
#include "GameFramework/SpringArmComponent.h"
#include "SeedBall.h"

namespace
{
	constexpr float EndFadeLead = 2.5f;
	constexpr float EndFadeDuration = 2.25f;
	constexpr float CameraReleaseDuration = 1.75f;
	constexpr float BarHeightFraction = 0.12f;
	constexpr float FlashTime = 0.7f;
	constexpr float CaptionFade = 0.6f;

	UOverlaySlot* Fill(UOverlaySlot* Slot)
	{
		Slot->SetHorizontalAlignment(HAlign_Fill);
		Slot->SetVerticalAlignment(VAlign_Fill);
		return Slot;
	}

	/** A picture that fills the screen without stretching, cropping its sides or top on a screen of another shape. */
	UImage* AddPicture(UWidgetTree* Tree, UOverlay* Root, FName Name)
	{
		UScaleBox* Box = Tree->ConstructWidget<UScaleBox>(UScaleBox::StaticClass(), FName(*(Name.ToString() + TEXT("Box"))));
		Box->SetStretch(EStretch::ScaleToFill);
		Fill(Root->AddChildToOverlay(Box));
		UImage* Image = Tree->ConstructWidget<UImage>(UImage::StaticClass(), Name);
		Box->AddChild(Image);
		return Image;
	}
}

void ULSIntroWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	UOverlay* Screen = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("Screen"));
	WidgetTree->RootWidget = Screen;
	PictureLayer = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("PictureLayer"));
	Fill(Screen->AddChildToOverlay(PictureLayer));

	UImage* Black = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Black"));
	Black->SetColorAndOpacity(FLinearColor::Black);
	Fill(PictureLayer->AddChildToOverlay(Black));

	UScaleBox* Frame = WidgetTree->ConstructWidget<UScaleBox>(UScaleBox::StaticClass(), TEXT("Frame"));
	Frame->SetStretch(EStretch::ScaleToFit);
	Fill(PictureLayer->AddChildToOverlay(Frame));
	USizeBox* FrameSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("FrameSize"));
	FrameSize->SetWidthOverride(1920.f);
	FrameSize->SetHeightOverride(1080.f);
	Frame->AddChild(FrameSize);
	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("Root"));
	Root->SetClipping(EWidgetClipping::ClipToBounds);
	FrameSize->AddChild(Root);

	BackImage = AddPicture(WidgetTree, Root, TEXT("BackImage"));
	FrontImage = AddPicture(WidgetTree, Root, TEXT("FrontImage"));

	Flash = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Flash"));
	Flash->SetColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.f));
	Fill(Root->AddChildToOverlay(Flash));

	CaptionText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("CaptionText"));
	FSlateFontInfo Font = CaptionText->GetFont();
	Font.FontObject = LoadObject<UFont>(nullptr, TEXT("/Game/UI/Fonts/F_Wildwood.F_Wildwood"));
	Font.TypefaceFontName = TEXT("Regular");
	Font.Size = 30;
	Font.LetterSpacing = 40;
	CaptionText->SetFont(Font);
	CaptionText->SetColorAndOpacity(FSlateColor(FLinearColor(0.93f, 0.88f, 0.74f)));
	CaptionText->SetShadowOffset(FVector2D(2.f, 2.f));
	CaptionText->SetShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.85f));
	CaptionText->SetJustification(ETextJustify::Center);
	CaptionText->SetRenderOpacity(0.f);
	UOverlaySlot* CaptionSlot = Root->AddChildToOverlay(CaptionText);
	CaptionSlot->SetHorizontalAlignment(HAlign_Center);
	CaptionSlot->SetVerticalAlignment(VAlign_Bottom);
	CaptionSlot->SetPadding(FMargin(60.f, 0.f, 60.f, 160.f));

	SkipButton = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("SkipButton"));
	FButtonStyle Style = SkipButton->GetStyle();
	Style.Normal.TintColor = FSlateColor(FLinearColor(0.f, 0.f, 0.f, 0.35f));
	Style.Hovered.TintColor = FSlateColor(FLinearColor(0.f, 0.f, 0.f, 0.6f));
	Style.Pressed.TintColor = FSlateColor(FLinearColor(0.f, 0.f, 0.f, 0.8f));
	SkipButton->SetStyle(Style);
	UTextBlock* SkipLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("SkipLabel"));
	SkipLabel->SetText(NSLOCTEXT("LastSeed", "IntroSkip", "Skip  >"));
	FSlateFontInfo SkipFont = SkipLabel->GetFont();
	SkipFont.FontObject = Font.FontObject;
	SkipFont.TypefaceFontName = TEXT("Heading");
	SkipFont.Size = 16;
	SkipLabel->SetFont(SkipFont);
	SkipLabel->SetColorAndOpacity(FSlateColor(FLinearColor(0.93f, 0.88f, 0.74f)));
	SkipButton->AddChild(SkipLabel);
	UOverlaySlot* SkipSlot = Root->AddChildToOverlay(SkipButton);
	SkipSlot->SetHorizontalAlignment(HAlign_Right);
	SkipSlot->SetVerticalAlignment(VAlign_Top);
	SkipSlot->SetPadding(FMargin(0.f, 152.f, 40.f, 0.f));
	SkipButton->OnClicked.AddDynamic(this, &ULSIntroWidget::RequestSkip);

	const auto AddBar = [this, Screen](const TCHAR* Name, EVerticalAlignment Align)
	{
		USizeBox* Bar = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), Name);
		UImage* Ink = WidgetTree->ConstructWidget<UImage>();
		Ink->SetColorAndOpacity(FLinearColor::Black);
		Bar->AddChild(Ink);
		Bar->SetVisibility(ESlateVisibility::HitTestInvisible);
		UOverlaySlot* Slot = Screen->AddChildToOverlay(Bar);
		Slot->SetHorizontalAlignment(HAlign_Fill);
		Slot->SetVerticalAlignment(Align);
		return Bar;
	};
	TopBar = AddBar(TEXT("TopBar"), VAlign_Top);
	BottomBar = AddBar(TEXT("BottomBar"), VAlign_Bottom);
}

void ULSIntroWidget::SetIntro(const TArray<FLSIntroShot>& InShots, USoundBase* InMusic, USoundBase* InVoiceOver)
{
	Shots = InShots;
	Music = InMusic;
	VoiceOver = InVoiceOver;
	TotalTime = ShotStart(Shots.Num());
}

void ULSIntroWidget::NativeConstruct()
{
	Super::NativeConstruct();
	// The opening pauses physics before a high PlayerStart can settle onto the path.
	if (ASeedBall* Ball = GetOwningPlayer() ? Cast<ASeedBall>(GetOwningPlayer()->GetPawn()) : nullptr)
	{
		if (UStaticMeshComponent* Body = Cast<UStaticMeshComponent>(Ball->GetRootComponent()))
		{
			FHitResult Ground;
			const FVector Start = Ball->GetActorLocation();
			FCollisionQueryParams Query(SCENE_QUERY_STAT(IntroSeedGround), false, Ball);
			if (GetWorld()->SweepSingleByChannel(Ground, Start, Start - FVector(0.f, 0.f, 2000.f), FQuat::Identity,
				ECC_WorldStatic, FCollisionShape::MakeSphere(Body->Bounds.SphereRadius), Query) &&
				!Ground.bStartPenetrating && Ground.Normal.Z > 0.5f)
			{
				Ball->TeleportBall(Ground.Location + FVector(0.f, 0.f, 1.f));
				if (USpringArmComponent* Arm = Ball->FindComponentByClass<USpringArmComponent>())
				{
					const bool bLag = Arm->bEnableCameraLag;
					Arm->bEnableCameraLag = false;
					Arm->TickComponent(0.f, LEVELTICK_All, nullptr);
					Arm->bEnableCameraLag = bLag;
				}
				if (GetOwningPlayer()->PlayerCameraManager) GetOwningPlayer()->PlayerCameraManager->UpdateCamera(0.f);
			}
		}
	}

	// UI sounds keep playing while the cutscene pauses gameplay.
	const auto PlayTrack = [this](USoundBase* Sound, float Volume) -> UAudioComponent*
	{
		UAudioComponent* Track = Sound ? UGameplayStatics::CreateSound2D(this, Sound, Volume) : nullptr;
		if (Track)
		{
			Track->bIsUISound = true;
			Track->Play();
		}
		return Track;
	};
	VoiceOverAudio = PlayTrack(VoiceOver, 1.f);
	MusicAudio = PlayTrack(Music, VoiceOverAudio ? 0.4f : 1.f);
	PlaybackStartTime = FPlatformTime::Seconds();
}

void ULSIntroWidget::NativeDestruct()
{
	RestoreCamera();
	if (IsValid(VoiceOverAudio))
	{
		VoiceOverAudio->Stop();
	}
	if (!bFinished && IsValid(MusicAudio))
	{
		MusicAudio->Stop();
	}
	Super::NativeDestruct();
}

void ULSIntroWidget::MatchSeedCamera(const FVector2D& ViewportSize)
{
	bMatchingStarted = true;
	APlayerController* PC = GetOwningPlayer();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn || !PC->PlayerCameraManager || ViewportSize.X <= 0.f || ViewportSize.Y <= 0.f) return;

	TArray<FVector> Corners;
	TInlineComponentArray<UStaticMeshComponent*> Meshes(Pawn);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (!Mesh->GetStaticMesh() || !Mesh->IsVisible() || Mesh->bHiddenInGame) continue;
		FVector Min, Max;
		Mesh->GetLocalBounds(Min, Max);
		for (int32 Corner = 0; Corner < 8; ++Corner)
			Corners.Add(Mesh->GetComponentTransform().TransformPosition(FVector(
				Corner & 1 ? Max.X : Min.X, Corner & 2 ? Max.Y : Min.Y, Corner & 4 ? Max.Z : Min.Z)));
	}
	if (Corners.IsEmpty()) return;

	FMinimalViewInfo View = PC->PlayerCameraManager->GetCameraCacheView();
	GameplayCameraLocation = View.Location;
	GameplayViewTarget = PC->GetViewTarget();
	// Use the live projection so ultrawide FOV and the gameplay camera's axis policy agree.
	FSceneViewProjectionData Projection;
	ULocalPlayer* Local = PC->GetLocalPlayer();
	if (Local && Local->ViewportClient && Local->ViewportClient->Viewport &&
		Local->GetProjectionData(Local->ViewportClient->Viewport, Projection))
		View.FOV = FMath::RadiansToDegrees(2.f * FMath::Atan(1.f / Projection.ProjectionMatrix.M[0][0]));
	View.AspectRatio = ViewportSize.X / ViewportSize.Y;
	View.bConstrainAspectRatio = false;
	View.AspectRatioAxisConstraint = EAspectRatioAxisConstraint::AspectRatio_MaintainXFOV;

	FActorSpawnParameters Spawn;
	Spawn.ObjectFlags |= RF_Transient;
	HandoffCamera = GetWorld()->SpawnActor<ACameraActor>(Spawn);
	if (!HandoffCamera) return;
	UCameraComponent* Camera = HandoffCamera->GetCameraComponent();
	Camera->SetFieldOfView(View.FOV);
	Camera->SetAspectRatio(View.AspectRatio);
	Camera->SetConstraintAspectRatio(false);
	Camera->bOverrideAspectRatioAxisConstraint = true;
	Camera->SetAspectRatioAxisConstraint(EAspectRatioAxisConstraint::AspectRatio_MaintainXFOV);
	Camera->PostProcessSettings = View.PostProcessSettings;
	Camera->PostProcessBlendWeight = View.PostProcessBlendWeight;

	// Painted seed bounds after the landing material's final 1.43x approach (ls_intro_motion.hlsl).
	const FVector2D ArtCenter(0.5036f, 0.5493f);
	constexpr float ArtHeight = 176.f / 1080.f * 1.43f;
	const float FrameScale = FMath::Min(ViewportSize.X / 1920.f, ViewportSize.Y / 1080.f);
	const FVector2D FrameSize = FVector2D(1920.f, 1080.f) * FrameScale;
	const FVector2D TargetCenter = ((ViewportSize - FrameSize) * 0.5f + ArtCenter * FrameSize) / ViewportSize;
	const float TargetHeight = ArtHeight * FrameSize.Y / ViewportSize.Y;
	const FBox Bounds(Corners);
	const FVector Center = Bounds.GetCenter();
	const FVector Forward = View.Rotation.Vector();
	const FVector Right = FRotationMatrix(View.Rotation).GetUnitAxis(EAxis::Y);
	const FVector Up = FRotationMatrix(View.Rotation).GetUnitAxis(EAxis::Z);
	const float TanH = FMath::Tan(FMath::DegreesToRadians(View.FOV * 0.5f));
	const float TanV = TanH / View.AspectRatio;
	float Distance = FMath::Max(150.f, FVector::DotProduct(Center - View.Location, Forward));
	FVector2D Correction = FVector2D::ZeroVector;
	for (int32 Iteration = 0; Iteration < 8; ++Iteration)
	{
		View.Location = Center - Forward * Distance
			- Right * ((TargetCenter.X - 0.5f) * 2.f * Distance * TanH + Correction.X)
			+ Up * ((TargetCenter.Y - 0.5f) * 2.f * Distance * TanV + Correction.Y);
		FMatrix ViewMatrix, ProjectionMatrix, ViewProjection;
		UGameplayStatics::CalculateViewProjectionMatricesFromMinimalView(View, {}, ViewMatrix, ProjectionMatrix, ViewProjection);
		FBox2D ScreenBounds(ForceInit);
		for (const FVector& Corner : Corners)
		{
			FVector2D Pixel;
			if (FSceneView::ProjectWorldToScreen(Corner, FIntRect(0, 0, FMath::RoundToInt(ViewportSize.X), FMath::RoundToInt(ViewportSize.Y)), ViewProjection, Pixel))
				ScreenBounds += Pixel / ViewportSize;
		}
		if (!ScreenBounds.bIsValid) break;
		const FVector2D Error = ScreenBounds.GetCenter() - TargetCenter;
		Correction.X -= Error.X * 2.f * Distance * TanH;
		Correction.Y -= Error.Y * 2.f * Distance * TanV;
		Distance *= FMath::Clamp(ScreenBounds.GetSize().Y / TargetHeight, 0.7f, 1.4f);
	}
	MatchedCameraLocation = View.Location;
	HandoffCamera->SetActorLocationAndRotation(View.Location, View.Rotation);
	PC->SetViewTarget(HandoffCamera);
}

void ULSIntroWidget::RestoreCamera()
{
	if (IsValid(HandoffCamera))
	{
		if (APlayerController* PC = GetOwningPlayer(); PC && PC->GetViewTarget() == HandoffCamera && IsValid(GameplayViewTarget))
			PC->SetViewTarget(GameplayViewTarget);
		HandoffCamera->Destroy();
		HandoffCamera = nullptr;
	}
}

void ULSIntroWidget::RequestSkip()
{
	if (SkipStartTime >= 0.0) return;
	SkipStartTime = FPlatformTime::Seconds();
	SkipPictureOpacity = PictureLayer->GetRenderOpacity();
	SkipBarTranslation = TopBar->GetRenderTransform().Translation.Y;
	if (IsValid(HandoffCamera)) SkipCameraLocation = HandoffCamera->GetActorLocation();
	SkipButton->SetIsEnabled(false);
	if (IsValid(MusicAudio)) MusicAudio->FadeOut(0.7f, 0.f);
	if (IsValid(VoiceOverAudio)) VoiceOverAudio->FadeOut(0.7f, 0.f);
}

float ULSIntroWidget::ShotStart(int32 Index) const
{
	float Start = 0.f;
	for (int32 Shot = 0; Shot < Index && Shot < Shots.Num(); ++Shot)
	{
		Start += Shots[Shot].Duration;
	}
	return Start;
}

void ULSIntroWidget::ApplyShot(UImage* Image, const FLSIntroShot& Shot, float Seconds) const
{
	const float Alpha = FMath::InterpEaseInOut(0.f, 1.f, FMath::Clamp(Seconds / Shot.Duration, 0.f, 1.f), 1.6f);
	const float Zoom = FMath::Lerp(Shot.StartZoom, Shot.EndZoom, Alpha);
	// Never shift further than the zoom leaves spare, so the picture's edge never comes into view.
	const float Margin = (Zoom - 1.f) * 0.5f;
	FVector2D Pan = FMath::Lerp(Shot.StartPan, Shot.EndPan, Alpha);
	Pan.X = FMath::Clamp(Pan.X, -Margin, Margin);
	Pan.Y = FMath::Clamp(Pan.Y, -Margin, Margin);
	// The transform is in the picture's own size, before the scale box fits it to the screen.
	const FVector2D Size = Shot.Image ? FVector2D(Shot.Image->GetSizeX(), Shot.Image->GetSizeY()) : FVector2D(1920.f, 1080.f);
	Image->SetRenderTransform(FWidgetTransform(Pan * Size, FVector2D(Zoom), FVector2D::ZeroVector, 0.f));
}

void ULSIntroWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (bFinished || Shots.IsEmpty())
	{
		return;
	}

	// The audio keeps running when the editor throttles the viewport.
	const float Elapsed = static_cast<float>(FPlatformTime::Seconds() - PlaybackStartTime);
	const float FadeStart = FMath::Max(0.f, TotalTime - EndFadeLead);
	const float ReleaseStart = FadeStart + EndFadeDuration;
	const float BarHeight = MyGeometry.GetLocalSize().Y * BarHeightFraction;
	TopBar->SetHeightOverride(BarHeight);
	BottomBar->SetHeightOverride(BarHeight);
	if (SkipStartTime >= 0.0)
	{
		const float Skip = FMath::SmoothStep(0.f, 0.8f, static_cast<float>(FPlatformTime::Seconds() - SkipStartTime));
		PictureLayer->SetRenderOpacity(SkipPictureOpacity * (1.f - Skip));
		const float BarOffset = FMath::Lerp(SkipBarTranslation, -BarHeight, Skip);
		TopBar->SetRenderTranslation(FVector2D(0.f, BarOffset));
		BottomBar->SetRenderTranslation(FVector2D(0.f, -BarOffset));
		if (IsValid(HandoffCamera)) HandoffCamera->SetActorLocation(FMath::Lerp(SkipCameraLocation, GameplayCameraLocation, Skip));
		if (IsValid(HandoffCamera)) GetOwningPlayer()->PlayerCameraManager->UpdateCamera(0.f);
		if (Skip >= 1.f) Finish();
		return;
	}
	if (Elapsed >= ReleaseStart + CameraReleaseDuration)
	{
		Finish();
		return;
	}

	int32 Index = 0;
	while (Index + 1 < Shots.Num() && Elapsed >= ShotStart(Index + 1))
	{
		++Index;
	}
	const FLSIntroShot& Shot = Shots[Index];
	if (Index != CurrentShot)
	{
		// The shot that was in front moves behind, and the new one starts fading in over it.
		if (Index > 0)
		{
			BackImage->SetBrushFromTexture(Shots[Index - 1].Image, true);
		}
		BackImage->SetRenderOpacity(Index > 0 ? 1.f : 0.f);
		FrontImage->SetBrushFromTexture(Shot.Image, true);
		ActiveMotion = nullptr;
		if (Shot.MotionMaterial)
		{
			FrontImage->SetBrushFromMaterial(Shot.MotionMaterial);
			ActiveMotion = FrontImage->GetDynamicMaterial();
			if (ActiveMotion && Shot.Image)
			{
				ActiveMotion->SetTextureParameterValue(TEXT("FrameTex"), Shot.Image);
			}
			FrontImage->SetRenderTransform(FWidgetTransform());
		}
		CurrentShot = Index;
	}

	const float Local = FMath::Min(Elapsed - ShotStart(Index), Shot.Duration);
	if (ActiveMotion)
	{
		ActiveMotion->SetScalarParameterValue(TEXT("ShotTime"), Local);
	}
	else
	{
		ApplyShot(FrontImage, Shot, Local);
	}
	const bool bFade = Shot.FadeIn > 0.f && (!ActiveMotion || Index == 0);
	const float FadeProgress = bFade ? FMath::Clamp(Local / Shot.FadeIn, 0.f, 1.f) : 1.f;
	FrontImage->SetRenderOpacity(FMath::SmoothStep(0.f, 1.f, FadeProgress));
	BackImage->SetRenderOpacity(Index > 0 && FadeProgress < 1.f ? 1.f : 0.f);
	if (Index > 0 && FadeProgress < 1.f)
	{
		ApplyShot(BackImage, Shots[Index - 1], Shots[Index - 1].Duration);
	}

	Flash->SetColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, Shot.bFlash && !ActiveMotion ? FMath::Clamp(1.f - Local / FlashTime, 0.f, 1.f) : 0.f));

	// A caption fades in when it changes and out before the next shot brings a different one.
	CaptionText->SetText(Shot.Caption);
	const bool bSameAsBefore = Index > 0 && Shots[Index - 1].Caption.EqualTo(Shot.Caption);
	const bool bSameAfter = Index + 1 < Shots.Num() && Shots[Index + 1].Caption.EqualTo(Shot.Caption);
	const float In = bSameAsBefore ? 1.f : FMath::Clamp((Local - 0.3f) / CaptionFade, 0.f, 1.f);
	const float Out = bSameAfter ? 1.f : FMath::Clamp((Shot.Duration - Local) / CaptionFade, 0.f, 1.f);
	CaptionText->SetRenderOpacity(Shot.Caption.IsEmpty() ? 0.f : FMath::Min(In, Out));

	if (Elapsed >= FadeStart && !bMatchingStarted)
	{
		int32 Width, Height;
		GetOwningPlayer()->GetViewportSize(Width, Height);
		MatchSeedCamera(FVector2D(Width, Height));
	}
	const float Dissolve = FMath::SmoothStep(FadeStart, ReleaseStart, Elapsed);
	const float Release = FMath::SmoothStep(ReleaseStart, ReleaseStart + CameraReleaseDuration, Elapsed);
	PictureLayer->SetRenderOpacity(1.f - Dissolve);
	SkipButton->SetRenderOpacity(1.f - Dissolve);
	TopBar->SetRenderTranslation(FVector2D(0.f, -BarHeight * Release));
	BottomBar->SetRenderTranslation(FVector2D(0.f, BarHeight * Release));
	if (IsValid(HandoffCamera))
	{
		HandoffCamera->SetActorLocation(FMath::Lerp(MatchedCameraLocation, GameplayCameraLocation, Release));
		// Gameplay remains paused until the bars are clear, so refresh the view explicitly.
		GetOwningPlayer()->PlayerCameraManager->UpdateCamera(0.f);
	}
}

void ULSIntroWidget::Finish()
{
	if (bFinished)
	{
		return;
	}
	bFinished = true;
	RestoreCamera();
	if (IsValid(MusicAudio))
	{
		MusicAudio->FadeOut(1.f, 0.f);
	}
	OnFinished.Broadcast();
}
