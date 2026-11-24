// See LSControlsWidget.h for this class's purpose, pattern and connections.

#include "LSControlsWidget.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Components/Button.h"
#include "Components/NativeWidgetHost.h"
#include "Components/TextBlock.h"
#include "Input/Events.h"
#include "LSGameInstance.h"
#include "Rendering/DrawElements.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCanvas.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	const FLinearColor ControlWhite = FLinearColor::White;
	const FLinearColor Muted(1.f, 1.f, 1.f, .52f);
	const FVector2D KeyboardOrigin(185, 126);

	class SControlArrows : public SLeafWidget
	{
	public:
		SLATE_BEGIN_ARGS(SControlArrows) {}
		SLATE_END_ARGS()

		void Construct(const FArguments& InArgs, TArray<TArray<FVector2f>> InPaths)
		{
			Paths = MoveTemp(InPaths);
		}

		virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D::ZeroVector; }

		virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
			FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle&, bool) const override
		{
			const FLinearColor LineColor(1.f, 1.f, 1.f, .76f);
			for (const TArray<FVector2f>& Path : Paths)
			{
				const FVector2f Tip = Path.Last();
				const FVector2f Back = (Path[Path.Num() - 2] - Tip).GetSafeNormal();
				const FVector2f Wing(-Back.Y, Back.X);
				const TArray<FVector2f> Head = { Tip + 10.f * Back + 4.f * Wing, Tip, Tip + 10.f * Back - 4.f * Wing };
				FSlateDrawElement::MakeLines(Elements, Layer, Geometry.ToPaintGeometry(), Path, ESlateDrawEffect::None, LineColor, true, 1.5f);
				FSlateDrawElement::MakeLines(Elements, Layer, Geometry.ToPaintGeometry(), Head, ESlateDrawEffect::None, LineColor, true, 1.5f);
			}
			return Layer;
		}

	private:
		TArray<TArray<FVector2f>> Paths;
	};

	struct FKeyboardKey
	{
		const TCHAR* Name;
		float Units = 1.f;
	};

	struct FControlBinding
	{
		FText Keys;
		FText Action;
	};

	TSharedRef<SWidget> DrawKey(const FText& Name, const FSlateFontInfo& Font, bool bActive, float Width, float Height)
	{
		static const FSlateRoundedBoxBrush KeyOutline(FLinearColor::Transparent, 5.f, FLinearColor(1.f, 1.f, 1.f, .52f), 1.15f);
		static const FSlateRoundedBoxBrush BoundKeyOutline(FLinearColor::Transparent, 5.f, ControlWhite, 1.7f);
		return SNew(SBox).WidthOverride(Width).HeightOverride(Height)
			[
				SNew(SBorder).BorderImage(bActive ? &BoundKeyOutline : &KeyOutline).HAlign(HAlign_Center).VAlign(VAlign_Center)
				[SNew(STextBlock).Text(Name).Font(Font).ColorAndOpacity(bActive ? ControlWhite : Muted)]
			];
	}

	TSharedRef<SWidget> DrawKeyboard(const FSlateFontInfo& Font, bool bStone, bool bDandelion, TMap<FString, FBox2D>& KeyBounds)
	{
		static const FSlateRoundedBoxBrush KeyboardOutline(FLinearColor::Transparent, 14.f, ControlWhite, 2.f);
		const bool bForms = bStone || bDandelion;
		const TSet<FString> BasicKeys = { TEXT("ESC"), TEXT("W"), TEXT("A"), TEXT("S"), TEXT("D"), TEXT("SPACE") };
		const TArray<TArray<FKeyboardKey>> Rows = {
			{ {TEXT("ESC"), 1.3f}, {TEXT("1")}, {TEXT("2")}, {TEXT("3")}, {TEXT("4")}, {TEXT("5")}, {TEXT("6")}, {TEXT("7")}, {TEXT("8")}, {TEXT("9")}, {TEXT("0")}, {TEXT("-")}, {TEXT("=")}, {TEXT("BACKSPACE"), 2.2f} },
			{ {TEXT("TAB"), 1.65f}, {TEXT("Q")}, {TEXT("W")}, {TEXT("E")}, {TEXT("R")}, {TEXT("T")}, {TEXT("Y")}, {TEXT("U")}, {TEXT("I")}, {TEXT("O")}, {TEXT("P")}, {TEXT("[")}, {TEXT("]")}, {TEXT("\\"), 1.85f} },
			{ {TEXT("CAPS"), 1.95f}, {TEXT("A")}, {TEXT("S")}, {TEXT("D")}, {TEXT("F")}, {TEXT("G")}, {TEXT("H")}, {TEXT("J")}, {TEXT("K")}, {TEXT("L")}, {TEXT(";")}, {TEXT("'")}, {TEXT("ENTER"), 2.55f} },
			{ {TEXT("SHIFT"), 2.5f}, {TEXT("Z")}, {TEXT("X")}, {TEXT("C")}, {TEXT("V")}, {TEXT("B")}, {TEXT("N")}, {TEXT("M")}, {TEXT(",")}, {TEXT(".")}, {TEXT("/")}, {TEXT("SHIFT"), 3.f} },
			{ {TEXT("CTRL"), 1.6f}, {TEXT("WIN"), 1.3f}, {TEXT("ALT"), 1.3f}, {TEXT("SPACE"), 6.4f}, {TEXT("ALT"), 1.3f}, {TEXT("FN"), 1.3f}, {TEXT("CTRL"), 2.3f} },
		};
		const TSharedRef<SVerticalBox> Keyboard = SNew(SVerticalBox);
		for (int32 Row = 0; Row < Rows.Num(); ++Row)
		{
			const TSharedRef<SHorizontalBox> Keys = SNew(SHorizontalBox);
			float X = KeyboardOrigin.X + 18.f;
			for (int32 Index = 0; Index < Rows[Row].Num(); ++Index)
			{
				const FKeyboardKey& Key = Rows[Row][Index];
				const FString Name(Key.Name);
				const bool bActive = BasicKeys.Contains(Name)
					|| (bForms && (Name == TEXT("1") || Name == TEXT("Q") || Name == TEXT("E")))
					|| (bStone && (Name == TEXT("2") || (Row == 4 && Index == 0)))
					|| (bDandelion && Name == TEXT("3"));
				const float Width = 56.f * Key.Units - 6.f;
				const FVector2D Corner(X, KeyboardOrigin.Y + 18.f + Row * 53.f);
				if (!KeyBounds.Contains(Name))
				{
					KeyBounds.Add(Name, FBox2D(Corner, Corner + FVector2D(Width, 47.f)));
				}
				Keys->AddSlot().AutoWidth().Padding(3.f)
					[DrawKey(FText::FromString(Name), Font, bActive, Width, 47.f)];
				X += Width + 6.f;
			}
			Keyboard->AddSlot().AutoHeight()[Keys];
		}

		return SNew(SBorder).BorderImage(&KeyboardOutline).Padding(15.f)[Keyboard];
	}

	TSharedRef<SWidget> DrawControls(const FSlateFontInfo& KeyFont, const FSlateFontInfo& BodyFont, bool bStone, bool bDandelion)
	{
		const TSharedRef<SCanvas> Canvas = SNew(SCanvas);
		TMap<FString, FBox2D> KeyBounds;
		Canvas->AddSlot().Position(KeyboardOrigin).Size(FVector2D(898, 295))
			[DrawKeyboard(KeyFont, bStone, bDandelion, KeyBounds)];

		const auto Label = [&](const FText& Text, FVector2D Position, FVector2D Size, EHorizontalAlignment Align = HAlign_Left)
		{
			Canvas->AddSlot().Position(Position).Size(Size)
			[
				SNew(SBox).HAlign(Align)
				[SNew(STextBlock).Text(Text).Font(BodyFont).ColorAndOpacity(ControlWhite)]
			];
		};
		TArray<TArray<FVector2f>> Paths;
		const auto Above = [&](const TCHAR* Key, const FText& Text, float X)
		{
			const FBox2D& Bounds = KeyBounds.FindChecked(Key);
			const float KeyX = Bounds.GetCenter().X;
			Label(Text, FVector2D(X - 90, 32), FVector2D(180, 35), HAlign_Center);
			Paths.Add({ {X, 69}, {X, 88}, {KeyX, 116}, {KeyX, float(Bounds.Min.Y)} });
		};

		Above(TEXT("ESC"), INVTEXT("Pause"), 170);
		if (bStone || bDandelion)
		{
			Above(TEXT("1"), INVTEXT("Seed"), 324);
			if (bStone)
			{
				Above(TEXT("2"), INVTEXT("Stone Shell"), 479);
			}
			if (bDandelion)
			{
				Above(TEXT("3"), INVTEXT("Dandelion"), 655);
			}

			Label(INVTEXT("Cycle forms"), FVector2D(9, 148), FVector2D(164, 36));
			const FBox2D& Q = KeyBounds.FindChecked(TEXT("Q"));
			const FBox2D& E = KeyBounds.FindChecked(TEXT("E"));
			const float QX = Q.GetCenter().X;
			const float EX = E.GetCenter().X;
			const float Top = Q.Min.Y;
			Paths.Add({ {114, 205}, {170, 205}, {183, 194}, {QX, 194}, {QX, Top} });
			Paths.Add({ {QX, 194}, {EX, 194}, {EX, Top} });
		}

		Label(INVTEXT("Roll\nW A S D"), FVector2D(9, 248), FVector2D(150, 60));
		const FBox2D& A = KeyBounds.FindChecked(TEXT("A"));
		const float AY = A.GetCenter().Y;
		Paths.Add({ {94, 280}, {170, 280}, {183, 246.5f}, {float(A.Min.X) - 7, 246.5f},
			{float(A.Min.X) - 7, AY}, {float(A.Min.X), AY} });

		const FBox2D& Space = KeyBounds.FindChecked(TEXT("SPACE"));
		const float SpaceX = Space.GetCenter().X;
		Label(bDandelion ? INVTEXT("Jump  /  Hold to glide as Dandelion") : INVTEXT("Jump"),
			FVector2D(SpaceX - 260, 484), FVector2D(520, 37), HAlign_Center);
		Paths.Add({ {SpaceX, 472}, {SpaceX, float(Space.Max.Y)} });

		if (bStone)
		{
			const FBox2D& Ctrl = KeyBounds.FindChecked(TEXT("CTRL"));
			const float CtrlX = Ctrl.GetCenter().X;
			Label(INVTEXT("Stone Shell slam"), FVector2D(85, 484), FVector2D(250, 36), HAlign_Center);
			Paths.Add({ {210, 472}, {210, 449}, {CtrlX, 431}, {CtrlX, float(Ctrl.Max.Y)} });
		}

		static const FSlateRoundedBoxBrush MouseOutline(FLinearColor::Transparent, 25.f, ControlWhite, 1.7f);
		Canvas->AddSlot().Position(FVector2D(878, 448)).Size(FVector2D(100, 85))
		[
			SNew(SBorder).BorderImage(&MouseOutline).HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(8.f, 11.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 4.f, 0.f)
				[DrawKey(INVTEXT("LMB"), KeyFont, bStone, 34.f, 33.f)]
				+ SHorizontalBox::Slot().AutoWidth()
				[DrawKey(INVTEXT("RMB"), KeyFont, false, 34.f, 33.f)]
			]
		];
		Label(INVTEXT("Look around"), FVector2D(1015, 499), FVector2D(200, 32));
		Paths.Add({ {1002, 514}, {978, 514} });
		if (bStone)
		{
			Label(INVTEXT("Slam (alternate)"), FVector2D(1015, 439), FVector2D(248, 36));
			Paths.Add({ {1002, 454}, {990, 435}, {909, 435}, {909, 459} });
		}

		return SNew(SBox).WidthOverride(1268.f).HeightOverride(561.f)
		[
			SNew(SOverlay)
			+ SOverlay::Slot()[Canvas]
			+ SOverlay::Slot()[SNew(SControlArrows, MoveTemp(Paths)).Visibility(EVisibility::HitTestInvisible)]
		];
	}
}

void ULSControlsWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	BackButton->OnClicked.AddDynamic(this, &ULSControlsWidget::HandleBack);
}

void ULSControlsWidget::Open()
{
	const ULSGameInstance* GI = GetGameInstance<ULSGameInstance>();
	const bool bStone = GI && GI->IsFormUnlocked(ESeedForm::Stone);
	const bool bDandelion = GI && GI->IsFormUnlocked(ESeedForm::Dandelion);
	const TArray<FControlBinding> Basics = {
		{ INVTEXT("W A S D"), INVTEXT("Roll") },
		{ INVTEXT("MOUSE"), INVTEXT("Look around") },
		{ INVTEXT("SPACE"), INVTEXT("Jump") },
		{ INVTEXT("ESC"), INVTEXT("Pause") },
	};
	TArray<FControlBinding> Forms, Abilities;
	if (bStone || bDandelion)
	{
		Forms.Add({ INVTEXT("1"), INVTEXT("Seed") });
		if (bStone)
		{
			Forms.Add({ INVTEXT("2"), INVTEXT("Stone Shell") });
			Abilities.Add({ INVTEXT("CTRL / LMB"), INVTEXT("Slam as Stone Shell") });
		}
		if (bDandelion)
		{
			Forms.Add({ INVTEXT("3"), INVTEXT("Dandelion") });
			Abilities.Add({ INVTEXT("HOLD SPACE"), INVTEXT("Glide as Dandelion") });
		}
		Forms.Add({ INVTEXT("Q / E"), INVTEXT("Cycle unlocked forms") });
	}

	FString Controls;
	const TArray<FControlBinding>* Groups[] = { &Basics, &Forms, &Abilities };
	for (const TArray<FControlBinding>* Group : Groups)
	{
		for (const FControlBinding& Binding : *Group)
		{
			Controls += FString::Printf(TEXT("%s   %s\n"), *Binding.Keys.ToString(), *Binding.Action.ToString());
		}
	}
	ControlsText->SetText(FText::FromString(Controls));

	if (UNativeWidgetHost* Layout = Cast<UNativeWidgetHost>(GetWidgetFromName(TEXT("KeyboardLayout"))))
	{
		FSlateFontInfo KeyFont = ControlsText->GetFont();
		KeyFont.Size = 16.f;
		KeyFont.TypefaceFontName = TEXT("Heading");
		FSlateFontInfo BodyFont = ControlsText->GetFont();
		BodyFont.Size = 24.f;
		Layout->SetContent(SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
			[DrawControls(KeyFont, BodyFont, bStone, bDandelion)]);
	}
	SetVisibility(ESlateVisibility::Visible);
	BackButton->SetFocus();
}

FReply ULSControlsWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	if (Event.GetKey() == EKeys::Escape)
	{
		HandleBack();
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(Geometry, Event);
}

void ULSControlsWidget::HandleBack()
{
	SetVisibility(ESlateVisibility::Collapsed);
	OnClosed.Broadcast();
}
